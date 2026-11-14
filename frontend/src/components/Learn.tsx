import { useEffect, useState } from 'react'
import { resolveTarget, type Resolved } from '../api'
import { useFlipbook, useSequence } from '../hooks'
import { LESSONS, type Lesson } from '../lessons'
import { readUrl, writeUrl } from '../url'
import Player from './Player'
import PlotsPanel from './PlotsPanel'

const PROGRESS_KEY = 'ultracool-learn-progress'
const loadProgress = (): string[] => {
  try {
    return JSON.parse(localStorage.getItem(PROGRESS_KEY) ?? '[]')
  } catch {
    return []
  }
}

/** Learn mode: the lesson path (left) and the selected lesson. Progress = lessons whose quiz was answered right. */
export default function Learn() {
  const [done, setDone] = useState(loadProgress)
  const [id, setId] = useState(() => {
    const fromUrl = readUrl().lesson
    return LESSONS.some((l) => l.id === fromUrl) ? fromUrl! : (LESSONS.find((l) => !done.includes(l.id)) ?? LESSONS[0]).id
  })
  const i = LESSONS.findIndex((l) => l.id === id)
  const open = (next: string) => {
    writeUrl({ lesson: next, frame: null })
    setId(next)
  }
  const complete = () => {
    if (done.includes(id)) return
    const next = [...done, id]
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(next))
    setDone(next)
  }
  return (
    <div className="flex h-full">
      <nav aria-label="Lessons" className="w-60 shrink-0 overflow-y-auto border-r border-slate-700 bg-slate-900 p-2 text-sm">
        <div className="mb-2 text-xs text-slate-400">
          {done.length}/{LESSONS.length} skills learned
          <div className="mt-1 h-1.5 rounded bg-slate-700">
            <div className="h-1.5 rounded bg-emerald-500" style={{ width: `${(100 * done.length) / LESSONS.length}%` }} />
          </div>
        </div>
        <ol className="space-y-1">
          {LESSONS.map((l, k) => (
            <li key={l.id}>
              <button
                aria-current={l.id === id ? 'step' : undefined}
                className={`flex w-full items-start gap-2 rounded px-2 py-1 text-left ${l.id === id ? 'bg-sky-900' : 'hover:bg-slate-800'}`}
                onClick={() => open(l.id)}
              >
                <span className={`mt-0.5 w-5 shrink-0 text-center text-xs ${done.includes(l.id) ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {done.includes(l.id) ? '✓' : k + 1}
                </span>
                <span>
                  {l.title}
                  <span className="block text-xs text-slate-400">{l.object}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
        {done.length > 0 && (
          <button
            className="mt-3 text-xs text-slate-500 underline"
            onClick={() => {
              localStorage.removeItem(PROGRESS_KEY)
              setDone([])
            }}
          >
            Reset progress
          </button>
        )}
      </nav>
      <LessonView
        key={id}
        lesson={LESSONS[i]}
        n={i + 1}
        onCorrect={complete}
        onNext={i < LESSONS.length - 1 ? () => open(LESSONS[i + 1].id) : undefined}
      />
    </div>
  )
}

function LessonView({ lesson, n, onCorrect, onNext }: { lesson: Lesson; n: number; onCorrect: () => void; onNext?: () => void }) {
  const [target, setTarget] = useState<Resolved | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { seq, error: seqError } = useSequence(target, {
    fov_deg: lesson.fov_deg,
    mjd_min: lesson.mjd_min,
    mjd_max: lesson.mjd_max,
    wise_exposures: lesson.wise_exposures,
  })
  const [fb, setFb] = useFlipbook({ bands: lesson.bands, deep: !!lesson.deep, frameId: null })

  useEffect(() => {
    if (lesson.pending) return
    if (lesson.ra !== undefined && lesson.dec !== undefined) {
      setTarget({ name: lesson.object, ra: lesson.ra, dec: lesson.dec, pmra_masyr: 0, pmdec_masyr: 0, epoch_yr: 2000, otype: null, sptype: null })
    } else if (lesson.target) {
      resolveTarget(lesson.target).then(setTarget).catch((e) => setError((e as Error).message))
    }
  }, [lesson])

  return (
    <div className="flex min-w-0 flex-1">
      <article className="w-[26rem] shrink-0 space-y-3 overflow-y-auto border-r border-slate-700 p-4 text-sm">
        <header>
          <div className="text-xs tracking-wide text-sky-400 uppercase">
            Lesson {n} · {lesson.skill}
          </div>
          <h2 className="text-xl font-semibold">{lesson.title}</h2>
          <div className="text-slate-400">{lesson.object}</div>
        </header>
        <p className="leading-relaxed text-slate-200">{lesson.story}</p>
        <aside className="rounded border-l-4 border-pink-400 bg-pink-950/40 p-3">
          <h3 className="mb-1 font-semibold text-pink-300">What to look for</h3>
          <p className="leading-relaxed">{lesson.look_for}</p>
        </aside>
        <Quiz key={lesson.id} quiz={lesson.quiz} onCorrect={onCorrect} />
        {onNext && (
          <button className="rounded bg-sky-700 px-3 py-1.5 hover:bg-sky-600" onClick={onNext}>
            Next lesson →
          </button>
        )}
      </article>
      <section aria-label="Flipbook" className="flex min-w-0 flex-1 flex-col">
        {lesson.pending ? (
          <div className="m-auto max-w-sm rounded border border-dashed border-slate-600 p-6 text-center text-slate-400">
            Example being prepared: we are picking the best real {lesson.object.toLowerCase()} to show here. The story and quiz already work.
          </div>
        ) : (
          <>
            <div className="shrink-0 overflow-y-auto">
              {(error || seqError) && <p className="p-2 text-xs text-red-400">{error ?? seqError}</p>}
              <div className="mx-auto max-w-md">
                <Player seq={seq} fb={fb} set={setFb} aladin={null} />
              </div>
            </div>
            <div className="min-h-64 flex-1 border-t border-slate-700 bg-slate-900">
              <PlotsPanel seq={seq} />
            </div>
          </>
        )}
      </section>
    </div>
  )
}

function Quiz({ quiz, onCorrect }: { quiz: Lesson['quiz']; onCorrect: () => void }) {
  const [choice, setChoice] = useState<number | null>(null)
  const [checked, setChecked] = useState(false)
  const right = checked && choice === quiz.answer_index
  return (
    <form
      className="rounded bg-slate-900 p-3"
      onSubmit={(e) => {
        e.preventDefault()
        setChecked(true)
        if (choice === quiz.answer_index) onCorrect()
      }}
    >
      <fieldset>
        <legend className="mb-2 font-semibold">Quiz: {quiz.question}</legend>
        {quiz.options.map((o, k) => (
          <label key={k} className="flex items-start gap-2 py-0.5">
            <input
              type="radio"
              name="quiz"
              className="mt-1"
              checked={choice === k}
              onChange={() => {
                setChoice(k)
                setChecked(false)
              }}
            />
            {o}
          </label>
        ))}
      </fieldset>
      <button className="mt-2 rounded bg-slate-700 px-3 py-1 enabled:hover:bg-slate-600 disabled:opacity-50" disabled={choice === null}>
        Check answer
      </button>
      {checked && (
        <p role="status" className={`mt-2 ${right ? 'text-emerald-300' : 'text-amber-300'}`}>
          {right ? 'Correct! ' : 'Not quite. Try again. '}
          {right && quiz.explanation}
        </p>
      )}
    </form>
  )
}
