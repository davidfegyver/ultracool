/** Status line for a result that is not there yet; spinner while still waiting. */
export default function Pending({ note, busy, className = '' }: { note: string | null; busy: boolean; className?: string }) {
  if (!note) return null
  return (
    <p role="status" className={`flex items-center gap-2 text-xs text-slate-500 ${className}`}>
      {busy && <span aria-hidden className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />}
      {note}
    </p>
  )
}
