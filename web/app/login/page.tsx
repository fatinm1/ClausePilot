'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { LogIn, Shield, Sparkles, ArrowLeft, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { login } from '../../lib/auth'
import { useAuth } from '../../lib/auth-context'

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>('')
  const router = useRouter()
  const { login: authLogin, user, loading } = useAuth()

  // Handle all side effects in a single useEffect
  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    
    try {
      const response = await login({ email, password })
      authLogin(response.user)
      // Redirect will be handled by the useEffect in the component
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  // Redirect based on user role after successful login
  useEffect(() => {
    if (user && !loading) {
      if (user.role === 'ADMIN') {
        router.push('/dashboard')
      } else {
        router.push('/user-dashboard')
      }
    }
  }, [user, loading, router])

  // Single return statement with conditional rendering
  return (
    <div className="min-h-screen bg-[#0B1220] text-[#E5E7EB]">
      {loading ? (
        // Loading state
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#60A5FA] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-[#E5E7EB]/80">Loading...</p>
          </div>
        </div>
      ) : user ? (
        // Redirect state
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#60A5FA] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-[#E5E7EB]/80">Redirecting to dashboard...</p>
          </div>
        </div>
      ) : (
        // Login form
        <>
      {/* Header */}
      <header className="bg-[#0B1220]/90 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-[#60A5FA] rounded-full animate-pulse" />
              <span className="text-xl font-semibold text-white">NDA Redline</span>
            </Link>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-[#E5E7EB]/60">Secure Login</span>
              <Link href="/" className="text-[#60A5FA] hover:text-[#60A5FA]/80 transition-colors flex items-center space-x-2">
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Home</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-md mx-auto px-6 py-16">
        {/* Login Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-8 shadow-2xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-[#60A5FA]/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-[#60A5FA]" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
            <p className="text-[#E5E7EB]/60">Sign in to your NDA Redline account</p>
          </div>

              {/* Error Display */}
              {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center space-x-3">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  <span className="text-red-400 text-sm">{error}</span>
                </div>
              )}

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#E5E7EB]/80 mb-2">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA] focus:ring-2 focus:ring-[#60A5FA]/20 transition-all duration-200"
                placeholder="Enter your email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[#E5E7EB]/80 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA] focus:ring-2 focus:ring-[#60A5FA]/20 transition-all duration-200"
                placeholder="Enter your password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
                  className="w-full bg-[#60A5FA] hover:bg-[#60A5FA]/80 disabled:bg-[#60A5FA]/40 disabled:cursor-not-allowed text-white py-3 rounded-lg font-semibold transition-colors flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Signing In...</span>
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  <span>Sign In</span>
                </>
              )}
            </button>
          </form>

              <div className="mt-6 text-center">
                <p className="text-[#E5E7EB]/60">
                  Don't have an account?{' '}
                  <Link href="/register" className="text-[#60A5FA] hover:text-[#60A5FA]/80 transition-colors">
                    Sign up here
              </Link>
                </p>
            </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
