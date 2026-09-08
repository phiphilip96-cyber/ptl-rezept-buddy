import { FormEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { Eingabe, Fehler, Knopf } from "../components/Ui";

export default function Login() {
  const [email, setEmail] = useState("");
  const [gesendet, setGesendet] = useState(false);
  const [laeuft, setLaeuft] = useState(false);
  const [params] = useSearchParams();

  async function senden(e: FormEvent) {
    e.preventDefault(); setLaeuft(true);
    try { await api.post("/auth/magic-link", { email }); setGesendet(true); } finally { setLaeuft(false); }
  }

  return (
    <main className="min-h-dvh flex flex-col px-6 pt-20 pb-10 max-w-md mx-auto">
      <div className="text-wald font-bold text-sm tracking-tight">Personal Training Lounge</div>
      <h1 className="text-4xl font-bold leading-[1.05] mt-2">Dein Rezept-Buddy.</h1>
      <p className="text-grau mt-3">Wochenpläne und Rezepte, die zu deinem Ziel passen – zwischen deinen Terminen mit Philip.</p>

      {gesendet ? (
        <div className="mt-10 rounded-2xl bg-wald-hell p-5">
          <p className="font-semibold">Link ist unterwegs.</p>
          <p className="text-sm mt-1">Wenn deine Adresse freigeschaltet ist, findest du in den nächsten Minuten eine E-Mail mit deinem Login-Link. Er gilt 30 Minuten.</p>
        </div>
      ) : (
        <form onSubmit={senden} className="mt-10 space-y-3">
          <Eingabe type="email" inputMode="email" autoComplete="email" required placeholder="deine@email.de"
            value={email} onChange={(e) => setEmail(e.target.value)} />
          <Knopf type="submit" className="w-full" disabled={laeuft}>Login-Link schicken</Knopf>
          <Fehler text={params.get("fehler") === "link" ? "Der Link ist abgelaufen oder wurde schon benutzt. Fordere einen neuen an." : null} />
        </form>
      )}
      <p className="text-xs text-grau mt-auto pt-10">Kein Passwort nötig. Du bekommst pro Login einen einmaligen Link. Zugang bekommst du von Philip.</p>
    </main>
  );
}
