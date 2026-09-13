export default function LoadingSpinner({ message = 'Loading…', size = 'md' }) {
  const sizes = { sm: 'w-5 h-5', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div className={`${sizes[size]} border-2 border-slate-600 border-t-accent rounded-full animate-spin`} />
      <p className="text-slate-400 text-sm">{message}</p>
    </div>
  )
}
