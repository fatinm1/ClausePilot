'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '../../lib/auth'
import { useAuth } from '../../lib/auth-context'
import { AuthShell, FormAlert, FullPageLoading } from '../../components/auth-shell'

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>('')
  const router = useRouter()
  const { login: authLogin, user, loading } = useAuth()

  useEffect(() => {
    if (user && !loading) {
      router.push(user.role === 'ADMIN' ? '/dashboard' : '/user-dashboard')
    }
  }, [user, loading, router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    try {
      const response = await login({ email, password })
      authLogin(response.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed. Check your email and password and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (loading) return <FullPageLoading />
  if (user) return <FullPageLoading label="Opening your workspace" />

  return (
    <AuthShell
      title={<span className="metal">Sign in</span>}
      intro="Pick up the NDAs waiting for review."
      footer={
        <>
          New to ClausePilot?{' '}
          <Link href="/register" className="text-white underline decoration-line-strong hover:decoration-white">
            Create an account
          </Link>
        </>
      }
    >
      <FormAlert>{error}</FormAlert>
      <form onSubmit={handleLogin} className="space-y-5" noValidate>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field"
            placeholder="you@firm.com"
          />
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="field"
          />
        </div>
        <button type="submit" disabled={isLoading || !email || !password} className="btn-metal mt-3 w-full">
          {isLoading ? (
            <>
              <span className="spinner" /> Signing in
            </>
          ) : (
            'Sign in'
          )}
        </button>
      </form>
    </AuthShell>
  )
}
