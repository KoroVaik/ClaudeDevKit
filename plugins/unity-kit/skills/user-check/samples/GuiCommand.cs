// SAMPLE to copy into a Unity project (unity-kit ships no Unity code). Put it in an Editor folder of an assembly that
// references the Unity CLI Loop package, rename the namespace and the tool name ("mygame-gui"), and name that tool in
// the profile: `## user-check`, `click-command`. The user check's click and drag steps call it with
// --action click|drag --x --y [--to-x --to-y --seconds].
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using io.github.hatayama.UnityCliLoop.ToolContracts;
using UnityEditor;
using UnityEngine;

namespace MyGame.Editor.Bridge
{
    // The mouse of an IMGUI panel for an agent's user check: "uloop mygame-gui --action click --x 0.5 --y 0.9" queues
    // mouse events into the Game view's own input queue (the one the Game view fills from the real mouse), so OnGUI gets
    // them as Event.current and its buttons and drags take them like a hand's. The Input System's mouse
    // (uloop simulate-mouse-input) does not reach IMGUI. Points are fractions of the game picture, from its top left.
    // Only in Play Mode.
    public sealed class GuiSchema : UnityCliLoopToolSchema
    {
        [Description("click (down, a frame, up), down, up, or drag (down at x,y, moves to to-x,to-y over seconds, up)")]
        public string Action { get; set; } = "click";
        [Description("Point across the game picture, 0 = left, 1 = right")]
        public float X { get; set; }
        [Description("Point down the game picture, 0 = top, 1 = bottom")]
        public float Y { get; set; }
        [Description("drag: where it ends across the picture")]
        public float ToX { get; set; }
        [Description("drag: where it ends down the picture")]
        public float ToY { get; set; }
        [Description("drag: seconds from the press to the release")]
        public float Seconds { get; set; } = .5f;
    }

    public sealed class GuiResponse : UnityCliLoopToolResponse
    {
        public string Message { get; set; }
        public float GameWidth { get; set; }
        public float GameHeight { get; set; }
        public float PixelX { get; set; }
        public float PixelY { get; set; }
        public int Events { get; set; }
    }

    [UnityCliLoopTool]
    public sealed class GuiTool : UnityCliLoopTool<GuiSchema, GuiResponse>
    {
        // Internal Unity API, read by reflection: if a Unity version drops it, the command refuses instead of guessing.
        private static readonly MethodInfo Queue = typeof(EditorGUIUtility).GetMethod("QueueGameViewInputEvent",
            BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);

        public override string ToolName => "mygame-gui";

        protected override Task<GuiResponse> ExecuteAsync(GuiSchema parameters, CancellationToken ct)
        {
            var response = new GuiResponse();
            string action = (parameters.Action ?? "").Trim();
            string refusal = !EditorApplication.isPlaying ? "not in Play Mode"
                : Queue == null ? "this Unity has no Game view input queue (EditorGUIUtility.QueueGameViewInputEvent)"
                : action is not ("click" or "down" or "up" or "drag") ? "unknown action " + action + "; known: click, down, up, drag"
                : null;
            if (refusal != null)
            {
                response.Success = false;
                response.Message = refusal;
                return Task.FromResult(response);
            }
            Vector2 size = Handles.GetMainGameViewSize();
            response.GameWidth = size.x;
            response.GameHeight = size.y;
            Vector2 from = Pixel(parameters.X, parameters.Y, size), to = Pixel(parameters.ToX, parameters.ToY, size);
            response.PixelX = from.x;
            response.PixelY = from.y;
            var events = new List<Func<Event>>();
            if (action is "click" or "down" or "drag") events.Add(() => Mouse(EventType.MouseDown, from, Vector2.zero));
            if (action == "drag")
            {
                // One move a frame at about 60 frames a second.
                int moves = Mathf.Max(1, Mathf.RoundToInt(Mathf.Max(0f, parameters.Seconds) * 60f));
                for (int i = 1; i <= moves; i++)
                {
                    Vector2 at = Vector2.Lerp(from, to, i / (float)moves), before = Vector2.Lerp(from, to, (i - 1) / (float)moves);
                    events.Add(() => Mouse(EventType.MouseDrag, at, at - before));
                }
            }
            if (action is "click" or "up" or "drag") events.Add(() => Mouse(EventType.MouseUp, action == "drag" ? to : from, Vector2.zero));
            response.Events = events.Count;
            response.Message = $"{action} at {from.x:0},{from.y:0} of {size.x:0}x{size.y:0} game pixels" +
                               (action == "drag" ? $" to {to.x:0},{to.y:0}" : "");
            // One event a frame, so the game sees a press, the moves and the release in separate frames as from a hand.
            var done = new TaskCompletionSource<GuiResponse>();
            int next = 0;
            void Step()
            {
                if (!EditorApplication.isPlaying)
                {
                    EditorApplication.update -= Step;
                    response.Success = false;
                    response.Message = "Play Mode ended";
                    done.TrySetResult(response);
                    return;
                }
                Queue.Invoke(null, new object[] { events[next++]() });
                if (next < events.Count) return;
                EditorApplication.update -= Step;
                done.TrySetResult(response);
            }
            EditorApplication.update += Step;
            return done.Task;
        }

        private static Vector2 Pixel(float x, float y, Vector2 size) => new Vector2(Mathf.Clamp01(x) * size.x, Mathf.Clamp01(y) * size.y);

        private static Event Mouse(EventType type, Vector2 at, Vector2 delta) =>
            new Event { type = type, button = 0, clickCount = type == EventType.MouseDown ? 1 : 0, mousePosition = at, delta = delta };
    }
}
