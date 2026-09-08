import { NavLink } from "react-router-dom";

const TABS = [
  { zu: "/heute", text: "Heute" }, { zu: "/chat", text: "Chat" }, { zu: "/plaene", text: "Pläne" }, { zu: "/ich", text: "Ich" },
];

/** Untere Tab-Leiste der Kunden-App (v2 §M1). Der Chat hat sie nicht, dort sitzt die Eingabe unten. */
export function TabLeiste() {
  return (
    <nav className="sticky bottom-0 z-10 bg-papier/95 backdrop-blur border-t border-linie grid grid-cols-4"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }} aria-label="Bereiche">
      {TABS.map((t) => (
        <NavLink key={t.zu} to={t.zu} className={({ isActive }) => `h-14 flex items-center justify-center text-sm font-medium ${isActive ? "text-wald" : "text-grau"}`}>
          {t.text}
        </NavLink>
      ))}
    </nav>
  );
}
