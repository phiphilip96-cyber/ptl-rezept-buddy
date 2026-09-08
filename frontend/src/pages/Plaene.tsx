import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Plan } from "../lib/typen";
import { PlanAnsicht } from "../components/Plaene";
import { Kopf, Leer } from "../components/Ui";

export function PlaeneListe() {
  const [plaene, setPlaene] = useState<Plan[] | null>(null);
  const nav = useNavigate();
  useEffect(() => { api.get<{ plaene: Plan[] }>("/plaene").then((d) => setPlaene(d.plaene)); }, []);
  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel="Meine Pläne" links={<button onClick={() => nav("/chat")} className="text-wald">Chat</button>} />
      {plaene && !plaene.length && <Leer titel="Noch nichts gespeichert." text="Frag den Buddy nach einem Wochenplan oder Rezept – alles landet automatisch hier." kind={<Link to="/chat" className="text-wald font-semibold">Zum Chat</Link>} />}
      <ul className="divide-y divide-linie px-4">
        {plaene?.map((p) => (
          <li key={p.id}>
            <Link to={`/plaene/${p.id}`} className="flex items-center gap-3 py-3">
              <span className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${p.typ === "wochenplan" ? "bg-wald text-white" : "bg-wald-hell text-wald"}`}>{p.typ === "wochenplan" ? "Wo" : "Re"}</span>
              <span className="flex-1 min-w-0">
                <span className="block truncate font-medium">{p.titel}</span>
                <span className="block text-xs text-grau">{new Date(p.erstellt_am).toLocaleDateString("de-DE")}</span>
              </span>
              {p.favorit && <span className="text-wald" aria-label="Favorit">★</span>}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

export function PlanDetail() {
  const { id } = useParams();
  const [plan, setPlan] = useState<Plan | null>(null);
  const nav = useNavigate();
  useEffect(() => { api.get<Plan>(`/plaene/${id}`).then(setPlan); }, [id]);
  async function favorit() {
    if (!plan) return;
    await api.patch(`/plaene/${plan.id}`, { favorit: !plan.favorit });
    setPlan({ ...plan, favorit: !plan.favorit });
  }
  return (
    <main className="min-h-dvh max-w-md mx-auto">
      <Kopf titel={plan?.titel ?? ""} links={<button onClick={() => nav(-1)} className="text-wald">Zurück</button>}
        rechts={plan && <button onClick={favorit} aria-pressed={plan.favorit} aria-label="Favorit" className={`text-2xl ${plan.favorit ? "text-wald" : "text-linie"}`}>★</button>} />
      <div className="px-4 py-4">{plan?.daten && <PlanAnsicht daten={plan.daten} />}</div>
    </main>
  );
}
