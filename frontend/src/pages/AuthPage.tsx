import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { login, signup } from '../api'
import { useShop } from '../store'

/** Log in (mode "login") and Create Account (mode "signup"). The server re-checks everything the form checks. */
export function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const { user, signIn } = useShop()
  const navigate = useNavigate()
  const location = useLocation()
  const next = (location.state as { from?: string } | null)?.from ?? '/products'
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value })

  const isSignup = mode === 'signup'
  const mismatch = isSignup && form.confirm_password.length > 0 && form.confirm_password !== form.password

  if (user && !busy) return <Navigate to={next} replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (isSignup && form.password.length < 8) return setError('Use at least 8 characters for your password.')
    if (isSignup && form.password !== form.confirm_password) return setError("Passwords don't match.")
    setBusy(true)
    try {
      const res = isSignup ? await signup(form) : await login({ email: form.email, password: form.password })
      signIn(res.token, res.user)
      navigate(next, { replace: true })
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  const type = showPassword ? 'text' : 'password'
  return (
    <div className="container auth-page">
      <div className="auth-card">
        <h1>{isSignup ? 'Create your account' : 'Log in'}</h1>
        <p className="muted">
          {isSignup ? 'Save your chats with our assistant and pick up where you left off.' : 'Welcome back. Log in so the assistant remembers your chats.'}
        </p>
        <form onSubmit={submit} className="form" noValidate={false}>
          {isSignup && (
            <div className="form-row">
              <label>
                First name
                <input value={form.first_name} onChange={set('first_name')} required maxLength={60} autoComplete="given-name" />
              </label>
              <label>
                Last name
                <input value={form.last_name} onChange={set('last_name')} required maxLength={60} autoComplete="family-name" />
              </label>
            </div>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={set('email')} required autoComplete={isSignup ? 'email' : 'username'} />
          </label>
          <label>
            <span className="label-row">
              Password
              <button type="button" className="link-button small" onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </span>
            <input type={type} value={form.password} onChange={set('password')} required maxLength={200}
              autoComplete={isSignup ? 'new-password' : 'current-password'} minLength={isSignup ? 8 : undefined} />
            {isSignup && <small className="muted">At least 8 characters. Avoid common passwords and your name or email.</small>}
          </label>
          {isSignup && (
            <label>
              Confirm password
              <input type={type} value={form.confirm_password} onChange={set('confirm_password')} required maxLength={200}
                autoComplete="new-password" aria-invalid={mismatch} className={mismatch ? 'input-error' : ''} />
              {mismatch && <small className="field-error">Passwords don't match.</small>}
            </label>
          )}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="btn btn-primary btn-block" disabled={busy || mismatch}>
            {busy ? 'Please wait…' : isSignup ? 'Create account' : 'Log in'}
          </button>
        </form>
        <p className="switch">
          {isSignup ? 'Already have an account?' : 'New to Campus Customs?'}{' '}
          <Link to={isSignup ? '/login' : '/signup'} state={location.state}>{isSignup ? 'Log in' : 'Create an account'}</Link>
        </p>
      </div>
    </div>
  )
}
