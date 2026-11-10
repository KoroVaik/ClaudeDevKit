// SAMPLE to copy into a Unity project (unity-kit ships no Unity code). Put it in an Editor folder of an assembly that
// references the Unity CLI Loop package, rename the namespace and the tool name ("mygame-state"), add the game's own
// fields, and name the tool in the profile: `## user-check`, `state-command`. The user check needs the five fields below;
// the profile's `ready` and the recipes' `expect-state` read any field by its name.
using System.Threading;
using System.Threading.Tasks;
using io.github.hatayama.UnityCliLoop.ToolContracts;
using UnityEditor;

namespace MyGame.Editor.Bridge
{
    // What the editor and the game are doing now: "uloop mygame-state". It reads only.
    public sealed class StateSchema : UnityCliLoopToolSchema { }

    public sealed class StateResponse : UnityCliLoopToolResponse
    {
        public string Message { get; set; }
        // Needed by the user check: it refuses to start in Play Mode, while compiling or with another scene than the profile's.
        public bool Playing { get; set; }
        public bool Compiling { get; set; }
        public string Scene { get; set; }
        // The game picture's size in pixels (the Game view's render size), for the points of click, drag and mouse.
        public float GameWidth { get; set; }
        public float GameHeight { get; set; }
        // The game's own fields go here, e.g. public bool Loaded { get; set; } for `ready` = `Loaded=true`.
    }

    [UnityCliLoopTool]
    public sealed class StateTool : UnityCliLoopTool<StateSchema, StateResponse>
    {
        public override string ToolName => "mygame-state";

        protected override Task<StateResponse> ExecuteAsync(StateSchema parameters, CancellationToken ct)
        {
            var game = Handles.GetMainGameViewSize();
            var response = new StateResponse
            {
                Playing = EditorApplication.isPlaying,
                Compiling = EditorApplication.isCompiling,
                Scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,
                GameWidth = game.x,
                GameHeight = game.y,
            };
            response.Message = response.Playing ? "in Play Mode" : "not in Play Mode";
            // Fill the game's own fields here, only in Play Mode.
            return Task.FromResult(response);
        }
    }
}
