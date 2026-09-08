/** Kleiner Markdown-Renderer (fett, kursiv, Listen, Überschriften, Absätze). Kein HTML-Passthrough. */
import { Fragment, ReactNode } from "react";

function inline(text: string): ReactNode[] {
  const teile: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m: RegExpExecArray | null, i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) teile.push(text.slice(last, m.index));
    const t = m[0];
    teile.push(t.startsWith("**") ? <strong key={i++}>{t.slice(2, -2)}</strong> : <em key={i++}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) teile.push(text.slice(last));
  return teile;
}

export function Markdown({ text }: { text: string }) {
  const bloecke: ReactNode[] = [];
  const zeilen = text.split("\n");
  let i = 0, key = 0;
  while (i < zeilen.length) {
    const z = zeilen[i];
    if (!z.trim()) { i++; continue; }
    if (/^#{1,3}\s/.test(z)) { bloecke.push(<h3 key={key++}>{inline(z.replace(/^#+\s/, ""))}</h3>); i++; continue; }
    if (/^\s*[-*]\s/.test(z)) {
      const items = [];
      while (i < zeilen.length && /^\s*[-*]\s/.test(zeilen[i])) items.push(<li key={i}>{inline(zeilen[i].replace(/^\s*[-*]\s/, ""))}</li>), i++;
      bloecke.push(<ul key={key++}>{items}</ul>); continue;
    }
    if (/^\s*\d+[.)]\s/.test(z)) {
      const items = [];
      while (i < zeilen.length && /^\s*\d+[.)]\s/.test(zeilen[i])) items.push(<li key={i}>{inline(zeilen[i].replace(/^\s*\d+[.)]\s/, ""))}</li>), i++;
      bloecke.push(<ol key={key++}>{items}</ol>); continue;
    }
    const absatz = [];
    while (i < zeilen.length && zeilen[i].trim() && !/^(#{1,3}\s|\s*[-*]\s|\s*\d+[.)]\s)/.test(zeilen[i])) absatz.push(zeilen[i]), i++;
    bloecke.push(<p key={key++}>{absatz.map((a, j) => <Fragment key={j}>{inline(a)}{j < absatz.length - 1 && <br />}</Fragment>)}</p>);
  }
  return <div className="buddy-text">{bloecke}</div>;
}
