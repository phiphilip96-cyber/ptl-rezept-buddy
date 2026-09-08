import { Rezept, Wochenplan } from "../lib/typen";

const KUERZEL: Record<string, string> = { Montag: "Mo", Dienstag: "Di", Mittwoch: "Mi", Donnerstag: "Do", Freitag: "Fr", Samstag: "Sa", Sonntag: "So" };

export function WochenplanTabelle({ plan }: { plan: Wochenplan }) {
  return (
    <div className="rounded-2xl border border-linie bg-white overflow-hidden">
      {plan.titel && <div className="px-4 py-3 font-semibold border-b border-linie">{plan.titel}</div>}
      <ol>
        {plan.tage.map((t, i) => {
          const kcal = t.mahlzeiten.reduce((s, m) => s + (m.kcal ?? 0), 0);
          const prot = t.mahlzeiten.reduce((s, m) => s + (m.protein_g ?? 0), 0);
          return (
            <li key={i} className="flex gap-3 px-4 py-3 border-b border-linie last:border-0">
              <div className="w-10 shrink-0">
                <div className="text-2xl font-bold leading-none text-wald">{KUERZEL[t.tag] ?? t.tag.slice(0, 2)}</div>
              </div>
              <div className="flex-1 min-w-0">
                {t.mahlzeiten.map((m, j) => (
                  <div key={j} className="py-1">
                    <div className="text-xs text-grau">{m.name}{m.kcal ? ` · ${m.kcal} kcal` : ""}{m.protein_g ? ` · ${m.protein_g} g P` : ""}</div>
                    <div className="text-[15px] leading-snug">{m.gericht}</div>
                  </div>
                ))}
                {kcal > 0 && <div className="text-xs text-grau mt-1 pt-1 border-t border-dashed border-linie">Tag: {kcal} kcal · {prot} g Protein</div>}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function RezeptKarte({ rezept }: { rezept: Rezept }) {
  const meta = [
    rezept.portionen && `${rezept.portionen} Portion${rezept.portionen === 1 ? "" : "en"}`,
    rezept.zeit_min && `${rezept.zeit_min} Min`,
    rezept.kcal_pro_portion && `${rezept.kcal_pro_portion} kcal`,
    rezept.protein_g_pro_portion && `${rezept.protein_g_pro_portion} g Protein`,
  ].filter(Boolean).join(" · ");
  return (
    <div className="rounded-2xl border border-linie bg-white p-4">
      <div className="font-semibold text-lg leading-tight">{rezept.titel ?? "Rezept"}</div>
      {meta && <div className="text-sm text-grau mt-1">{meta}{rezept.kcal_pro_portion ? " je Portion" : ""}</div>}
      <div className="mt-4 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[15px]">
        {rezept.zutaten.map((z, i) => (
          <div key={i} className="contents">
            <span className="text-grau whitespace-nowrap">{z.menge ?? ""}</span>
            <span>{z.name}</span>
          </div>
        ))}
      </div>
      <ol className="mt-4 space-y-2 list-none">
        {rezept.schritte.map((s, i) => (
          <li key={i} className="flex gap-3 text-[15px] leading-snug">
            <span className="w-6 h-6 shrink-0 rounded-full bg-wald-hell text-wald text-xs font-semibold flex items-center justify-center">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function PlanAnsicht({ daten }: { daten: Wochenplan | Rezept }) {
  return daten.typ === "wochenplan" ? <WochenplanTabelle plan={daten} /> : <RezeptKarte rezept={daten} />;
}
