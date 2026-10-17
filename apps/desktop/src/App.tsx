import { useEffect, useRef, useState, type FormEvent } from "react";
import { pingRuntime, sendChatMessage } from "./bridge/runtime";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  failed?: boolean;
};

const welcomeMessage: ChatMessage = {
  id: 1,
  role: "assistant",
  text: "Hi, I'm Sanvik. Tell me what you would like me to do on your computer.",
};

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [status, setStatus] = useState("Connecting");
  const [busy, setBusy] = useState(false);
  const nextMessageId = useRef(2);
  const conversationId = useRef(crypto.randomUUID());
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void pingRuntime()
      .then(() => setStatus("Ready"))
      .catch(() => setStatus("Python unavailable"));
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function addMessage(message: Omit<ChatMessage, "id">) {
    const newMessage = { ...message, id: nextMessageId.current };
    nextMessageId.current += 1;
    setMessages((currentMessages) => [...currentMessages, newMessage]);
  }

  async function sendMessage() {
    const userText = input.trim();

    if (!userText || busy) {
      return;
    }

    addMessage({ role: "user", text: userText });
    setInput("");
    setBusy(true);
    setStatus("Working");

    try {
      const reply = await sendChatMessage(userText, conversationId.current);
      addMessage({ role: "assistant", text: reply });
    } catch (error: unknown) {
      addMessage({
        role: "assistant",
        text: "I could not complete that request. " + String(error),
        failed: true,
      });
    } finally {
      setBusy(false);
      setStatus("Ready");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage();
  }

  return (
    <main className="chat-app">
      <header className="app-header">
        <div className="brand-mark" aria-hidden="true">S</div>
        <div>
          <h1>Sanvik AI</h1>
          <p className="status" role="status">
            <span className={"status-dot " + (status === "Ready" ? "online" : "")} />
            {status}
          </p>
        </div>
      </header>

      <section className="message-list" aria-live="polite" aria-label="Conversation">
        {messages.map((message) => (
          <article key={message.id} className={"message-row " + message.role}>
            <div className={"message-bubble " + (message.failed ? "failed" : "")}>
              <p>{message.text}</p>
            </div>
          </article>
        ))}

        {busy && (
          <article className="message-row assistant">
            <div className="message-bubble typing" aria-label="Sanvik is working">
              <span />
              <span />
              <span />
            </div>
          </article>
        )}
        <div ref={messagesEnd} />
      </section>

      <form className="composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="message">Message Sanvik</label>
        <input
          id="message"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask Sanvik to do something..."
          autoComplete="off"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()} aria-label="Send message">
          <span aria-hidden="true">&uarr;</span>
        </button>
      </form>
    </main>
  );
}
