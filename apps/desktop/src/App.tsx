import { useEffect, useState, type FormEvent } from "react";
import { pingRuntime, sendMessage } from "./bridge/runtime";

export default function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");
  const [status, setStatus] = useState("Connecting to Python...");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    void pingRuntime()
      .then(setStatus)
      .catch((error: unknown) => setStatus(`Python unavailable: ${String(error)}`));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim() || sending) return;

    setSending(true);
    setResponse("");
    try {
      const reply = await sendMessage(message);
      setResponse(reply);
      setStatus("Python connected");
    } catch (error: unknown) {
      setResponse(`Request failed: ${String(error)}`);
    } finally {
      setSending(false);
    }
  }

  return (
    <main>
      <h1>Sanvik AI</h1>
      <p role="status">{status}</p>
      <form onSubmit={(event) => void submit(event)}>
        <label htmlFor="message">Message</label>
        <input
          id="message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Hello Sanvik"
          autoComplete="off"
        />
        <button type="submit" disabled={sending || !message.trim()}>
          {sending ? "Sending..." : "Send"}
        </button>
      </form>
      <section aria-live="polite">
        <h2>Python response</h2>
        <p>{response || "No response yet."}</p>
      </section>
    </main>
  );
}
