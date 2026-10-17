import { useEffect, useState, type FormEvent } from "react";
import { pingRuntime, runTask } from "./bridge/runtime";
import type { Execution, Plan } from "./bridge/types";

export default function App() {
  const [task, setTask] = useState("");
  const [submittedTask, setSubmittedTask] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Connecting to Python...");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void pingRuntime()
      .then(setStatus)
      .catch((error: unknown) => setStatus(`Python unavailable: ${String(error)}`));
  }, []);

  async function start() {
    if (!task.trim() || busy) return;

    setBusy(true);
    setPlan(null);
    setExecution(null);
    setError("");
    setSubmittedTask(task.trim());
    setStatus("Planning and running task...");

    try {
      const result = await runTask(task);
      setPlan(result.plan);
      setExecution(result.execution);
      setStatus(result.execution.completed ? "Task completed" : "Task stopped");
    } catch (error: unknown) {
      setError(`Task failed: ${String(error)}`);
      setStatus("Task failed");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void start();
  }

  return (
    <main>
      <h1>Sanvik AI</h1>
      <p role="status">{status}</p>
      <form onSubmit={submit}>
        <label htmlFor="task">Task</label>
        <input
          id="task"
          value={task}
          onChange={(event) => setTask(event.target.value)}
          placeholder="Open Notepad and type Hello"
          autoComplete="off"
        />
        <button type="submit" disabled={busy || !task.trim()}>
          Run task
        </button>
      </form>
      <section aria-live="polite">
        <h2>Result</h2>
        {error && <p role="alert">{error}</p>}
        {busy && <p>Please wait...</p>}
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
                  {execution?.steps[index] && (
                    <div>{execution.steps[index].success ? "Verified" : "Failed"}: {execution.steps[index].message}</div>
                  )}
                </li>
              ))}
            </ol>
            {execution && <p>{execution.completed ? "All steps verified." : "Execution stopped before all steps completed."}</p>}
          </>
        )}
        {!busy && !plan && !error && <p>No task yet.</p>}
      </section>
    </main>
  );
}
