import { useEffect, useState, type FormEvent } from "react";
import { pingRuntime, planTask } from "./bridge/runtime";
import type { Plan } from "./bridge/types";

export default function App() {
  const [task, setTask] = useState("");
  const [submittedTask, setSubmittedTask] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Connecting to Python...");
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    void pingRuntime()
      .then(setStatus)
      .catch((error: unknown) => setStatus(`Python unavailable: ${String(error)}`));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!task.trim() || planning) return;

    setPlanning(true);
    setPlan(null);
    setError("");
    setSubmittedTask(task.trim());
    try {
      const result = await planTask(task);
      setPlan(result);
      setStatus("Plan ready");
    } catch (error: unknown) {
      setError(`Planning failed: ${String(error)}`);
    } finally {
      setPlanning(false);
    }
  }

  return (
    <main>
      <h1>Sanvik AI</h1>
      <p role="status">{status}</p>
      <form onSubmit={(event) => void submit(event)}>
        <label htmlFor="task">Task</label>
        <input
          id="task"
          value={task}
          onChange={(event) => setTask(event.target.value)}
          placeholder="Open Notepad and type Hello"
          autoComplete="off"
        />
        <button type="submit" disabled={planning || !task.trim()}>
          {planning ? "Planning..." : "Create plan"}
        </button>
      </form>
      <section aria-live="polite">
        <h2>Plan</h2>
        {error && <p role="alert">{error}</p>}
        {planning && <p>Creating a plan...</p>}
        {plan && (
          <>
            <p><strong>Task:</strong> {submittedTask}</p>
            <p><strong>Goal:</strong> {plan.goal}</p>
            <ol>
              {plan.steps.map((step, index) => (
                <li key={index}>
                  <strong>{step.action}</strong>
                  {Object.keys(step.parameters).length > 0 && (
                    <span> ({Object.entries(step.parameters).map(([key, value]) => `${key}: ${value}`).join(", ")})</span>
                  )}
                  <div>Expected: {step.expected_result}</div>
                  <div>Risk: {step.risk_level}</div>
                </li>
              ))}
            </ol>
            <p>Plan only. No actions have been performed.</p>
          </>
        )}
        {!planning && !plan && !error && <p>No plan yet.</p>}
      </section>
    </main>
  );
}
