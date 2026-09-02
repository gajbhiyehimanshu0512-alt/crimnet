import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { ingestFIR, ingestCDR, ingestFinancial, ingestSurveillance, ingestText } from '../api/client'
import { Upload, FileText, Phone, DollarSign, Eye, Type, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const SOURCE_TYPES = [
  { key: 'fir',          label: 'FIR / Police Report',      icon: FileText,   ext: '.pdf,.txt,.doc,.docx', fn: ingestFIR,          color: 'text-red-400' },
  { key: 'cdr',          label: 'Call Detail Records',      icon: Phone,      ext: '.csv,.xlsx,.xls',      fn: ingestCDR,          color: 'text-green-400' },
  { key: 'financial',    label: 'Financial Transactions',   icon: DollarSign, ext: '.csv,.xlsx,.xls',      fn: ingestFinancial,    color: 'text-yellow-400' },
  { key: 'surveillance', label: 'Surveillance Report',      icon: Eye,        ext: '.txt,.pdf',            fn: null,               color: 'text-blue-400' },
  { key: 'text',         label: 'Free-text Intel',          icon: Type,       ext: null,                   fn: null,               color: 'text-purple-400' },
]

function DropZone({ source, onResult }) {
  const [status, setStatus]   = useState('idle')   // idle | uploading | success | error
  const [result, setResult]   = useState(null)
  const [textInput, setText]  = useState('')

  const onDrop = useCallback(async (files) => {
    if (!files.length) return
    const file = files[0]
    setStatus('uploading')
    try {
      let res
      if (source.fn) {
        res = await source.fn(file)
      } else if (source.key === 'surveillance') {
        const text = await file.text()
        res = await ingestSurveillance(text)
      }
      setResult(res?.data)
      setStatus('success')
      toast.success(`Ingested ${res?.data?.entities_stored || 0} entities`)
      onResult?.(res?.data)
    } catch (e) {
      setStatus('error')
      toast.error(`Ingestion failed: ${e.response?.data?.detail || e.message}`)
    }
  }, [source])

  const handleTextIngest = async () => {
    if (!textInput.trim()) return
    setStatus('uploading')
    try {
      const res = await ingestText(textInput, source.label)
      setResult(res.data)
      setStatus('success')
      toast.success(`Ingested ${res.data.entities_stored || 0} entities`)
      onResult?.(res.data)
    } catch (e) {
      setStatus('error')
      toast.error('Text ingestion failed.')
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: source.ext ? Object.fromEntries(
      source.ext.split(',').map(e => [`application/${e.slice(1)}`, [e]])
    ) : undefined,
    disabled: status === 'uploading' || source.key === 'text',
  })

  const Icon = source.icon

  return (
    <div className="card space-y-4">
      <div className={clsx('flex items-center gap-3', source.color)}>
        <Icon size={20} />
        <h3 className="font-semibold text-white">{source.label}</h3>
        {status === 'success' && <CheckCircle size={16} className="ml-auto text-green-400" />}
        {status === 'error'   && <XCircle     size={16} className="ml-auto text-red-400" />}
      </div>

      {source.key === 'text' ? (
        <div className="space-y-2">
          <textarea
            value={textInput}
            onChange={e => setText(e.target.value)}
            placeholder="Paste intelligence report, witness statement, or any free text here…"
            rows={5}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent resize-none"
          />
          <button
            onClick={handleTextIngest}
            disabled={status === 'uploading' || !textInput.trim()}
            className="w-full py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {status === 'uploading' ? <><Loader2 size={14} className="animate-spin" /> Processing…</> : 'Ingest Text'}
          </button>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors',
            isDragActive ? 'border-accent bg-accent/10' : 'border-border hover:border-slate-500',
            status === 'uploading' && 'opacity-50 pointer-events-none'
          )}
        >
          <input {...getInputProps()} />
          {status === 'uploading' ? (
            <div className="flex flex-col items-center gap-2 text-slate-400">
              <Loader2 size={28} className="animate-spin" />
              <span className="text-sm">Processing…</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-slate-400">
              <Upload size={28} className={isDragActive ? 'text-accent' : ''} />
              <p className="text-sm">{isDragActive ? 'Drop to ingest' : `Drag & drop or click to upload`}</p>
              <p className="text-xs">{source.ext}</p>
            </div>
          )}
        </div>
      )}

      {status === 'success' && result && (
        <div className="bg-green-900/20 border border-green-800 rounded-lg p-3 text-xs space-y-1">
          <div className="text-green-400 font-semibold">✓ Ingestion successful</div>
          <div className="text-slate-300">Entities stored: <span className="text-white">{result.entities_stored}</span></div>
          <div className="text-slate-300">Relationships: <span className="text-white">{result.relationships_stored}</span></div>
          {result.suspicious_count > 0 && (
            <div className="text-orange-400">⚠ {result.suspicious_count} suspicious transactions flagged</div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DataIngestion() {
  const [results, setResults] = useState([])

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Upload className="text-accent" size={24} />
          Data Ingestion
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload intelligence documents to populate the criminal network graph.
          Supported: FIRs, CDRs, financial records, surveillance reports, and free text.
        </p>
      </div>

      <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 text-sm text-blue-300">
        <strong>Tip:</strong> After uploading documents, go to the Dashboard and click <strong>Run Analytics</strong>
        to compute centrality, detect communities, and identify anomalies.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {SOURCE_TYPES.map(src => (
          <DropZone
            key={src.key}
            source={src}
            onResult={r => setResults(prev => [{ ...r, source: src.label, ts: new Date().toLocaleTimeString() }, ...prev])}
          />
        ))}
      </div>

      {/* Ingestion Log */}
      {results.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-white mb-3">Ingestion Log</h3>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="flex items-center gap-3 text-sm border-b border-border/50 pb-2">
                <CheckCircle size={14} className="text-green-400 flex-shrink-0" />
                <span className="text-slate-400">{r.ts}</span>
                <span className="text-slate-300">{r.source}</span>
                <span className="ml-auto text-green-400">{r.entities_stored} entities · {r.relationships_stored} relations</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
