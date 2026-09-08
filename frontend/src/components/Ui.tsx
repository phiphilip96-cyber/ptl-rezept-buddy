import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

export function Knopf({ variante = "voll", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "voll" | "leise" | "text" }) {
  const basis = "inline-flex items-center justify-center rounded-full px-5 h-12 font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed";
  const stil = variante === "voll" ? "bg-wald text-white active:bg-tinte"
    : variante === "leise" ? "bg-wald-hell text-wald active:bg-linie"
    : "text-wald h-auto px-2";
  return <button className={`${basis} ${stil} ${className}`} {...p} />;
}

export function Feld({ label, hinweis, children }: { label: string; hinweis?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm text-grau mb-1">{label}</span>
      {children}
      {hinweis && <span className="block text-xs text-grau mt-1">{hinweis}</span>}
    </label>
  );
}

const eingabeStil = "w-full h-12 rounded-xl border border-linie bg-white px-4 text-tinte placeholder:text-grau/60 focus:border-wald";

export function Eingabe(p: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={eingabeStil} {...p} />;
}

export function Auswahl(p: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${eingabeStil} appearance-none`} {...p} />;
}

export function Chips({ werte, aktiv, onToggle, frei, onFrei }: {
  werte: string[]; aktiv: string[]; onToggle: (w: string) => void; frei?: boolean; onFrei?: (w: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {[...new Set([...werte, ...aktiv])].map((w) => {
        const an = aktiv.includes(w);
        return (
          <button type="button" key={w} onClick={() => onToggle(w)} aria-pressed={an}
            className={`h-9 px-3 rounded-full border text-sm transition ${an ? "bg-wald border-wald text-white" : "bg-white border-linie text-tinte"}`}>
            {w}
          </button>
        );
      })}
      {frei && (
        <input placeholder="Weitere…" className="h-9 px-3 rounded-full border border-dashed border-linie bg-transparent text-sm w-28 focus:border-wald"
          onKeyDown={(e) => {
            const el = e.currentTarget;
            if (e.key === "Enter" && el.value.trim()) { e.preventDefault(); onFrei?.(el.value.trim().toLowerCase()); el.value = ""; }
          }} />
      )}
    </div>
  );
}

export function Kopf({ titel, links, rechts }: { titel: ReactNode; links?: ReactNode; rechts?: ReactNode }) {
  return (
    <header className="sticky top-0 z-10 bg-papier/95 backdrop-blur border-b border-linie px-4 h-14 flex items-center gap-3">
      <div className="w-10">{links}</div>
      <div className="flex-1 text-center font-semibold truncate">{titel}</div>
      <div className="w-10 flex justify-end">{rechts}</div>
    </header>
  );
}

export function Leer({ titel, text, kind }: { titel: string; text: string; kind?: ReactNode }) {
  return (
    <div className="px-6 py-16 text-center">
      <p className="font-semibold text-lg">{titel}</p>
      <p className="text-grau mt-1">{text}</p>
      {kind && <div className="mt-6">{kind}</div>}
    </div>
  );
}

export function Fehler({ text }: { text: string | null }) {
  return text ? <p role="alert" className="text-warn text-sm mt-2">{text}</p> : null;
}
