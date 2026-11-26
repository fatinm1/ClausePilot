'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register } from '../../lib/auth'
import { useAuth } from '../../lib/auth-context'
import { AuthShell, FieldError, FormAlert, FullPageLoading } from '../../components/auth-shell'

export default function RegisterPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    firmName: '',
    agreeToTerms: false
  })
  const [errors, setErrors] = useState<{[key: string]: string}>({})
  const [submitError, setSubmitError] = useState('')
  const router = useRouter()
  const { login: authLogin, user, loading } = useAuth()

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
    // Clear submit error when user makes changes
    if (submitError) {
      setSubmitError('')
    }
  }

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {}
    
    if (!formData.firstName.trim()) newErrors.firstName = 'First name is required'
    if (!formData.lastName.trim()) newErrors.lastName = 'Last name is required'
    if (!formData.email.trim()) newErrors.email = 'Email is required'
    if (!formData.password) newErrors.password = 'Password is required'
    if (formData.password.length < 8) newErrors.password = 'Password must be at least 8 characters'
    if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'The two passwords don’t match.'
    if (!formData.firmName.trim()) newErrors.firmName = 'Firm name is required'
    if (!formData.agreeToTerms) newErrors.agreeToTerms = 'Tick the box to accept the terms before continuing.'

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    setIsLoading(true)
    setSubmitError('')
    
    try {
      const response = await register({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        password: formData.password,
        firmName: formData.firmName
      })
      
      // Use auth context to login
      authLogin(response.user)
      
      // Redirect will be handled by the useEffect in the component
    } catch (error: any) {
      setSubmitError(error.message || 'Registration failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Redirect based on user role after successful registration
  useEffect(() => {
    if (user && !loading) {
      if (user.role === 'ADMIN') {
        router.push('/dashboard')
      } else {
        router.push('/user-dashboard')
      }
    }
  }, [user, loading, router])

  const field = (
    name: 'firstName' | 'lastName' | 'email' | 'firmName' | 'password' | 'confirmPassword',
    label: string,
    type = 'text',
    autoComplete?: string,
    hint?: string
  ) => (
    <div>
      <label htmlFor={name} className="label">{label}</label>
      <input
        id={name}
        type={type}
        autoComplete={autoComplete}
        value={formData[name] as string}
        onChange={(e) => handleInputChange(name, e.target.value)}
        aria-invalid={errors[name] ? true : undefined}
        aria-describedby={errors[name] ? `${name}-error` : hint ? `${name}-hint` : undefined}
        className="field"
      />
      {hint && !errors[name] && <p id={`${name}-hint`} className="mt-2 text-sm text-fg-3">{hint}</p>}
      <FieldError id={`${name}-error`}>{errors[name]}</FieldError>
    </div>
  )

  if (loading) return <FullPageLoading />
  if (user) return <FullPageLoading label="Opening your workspace" />

  return (
    <AuthShell
      title={<span className="metal">Create an account</span>}
      intro="Your firm name goes into the signature block of every redline you download."
      footer={
        <>
          Already have an account?{' '}
          <Link href="/login" className="text-white underline decoration-line-strong hover:decoration-white">
            Sign in
          </Link>
        </>
      }
    >
      <FormAlert>{submitError}</FormAlert>
      <form onSubmit={handleRegister} className="space-y-5" noValidate>
        <div className="grid gap-5 sm:grid-cols-2">
          {field('firstName', 'First name', 'text', 'given-name')}
          {field('lastName', 'Last name', 'text', 'family-name')}
        </div>
        {field('email', 'Work email', 'email', 'email')}
        {field('firmName', 'Firm name', 'text', 'organization')}
        {field('password', 'Password', 'password', 'new-password', 'At least 8 characters.')}
        {field('confirmPassword', 'Confirm password', 'password', 'new-password')}
        <div>
          <label htmlFor="agreeToTerms" className="flex cursor-pointer items-start gap-3 text-[0.95rem] text-fg-2">
            <input
              id="agreeToTerms"
              type="checkbox"
              checked={formData.agreeToTerms}
              onChange={(e) => handleInputChange('agreeToTerms', e.target.checked)}
              aria-invalid={errors.agreeToTerms ? true : undefined}
              className="mt-[3px] h-4 w-4 shrink-0 accent-[#cbced2]"
            />
            I agree to the terms of use and privacy policy.
          </label>
          <FieldError id="agreeToTerms-error">{errors.agreeToTerms}</FieldError>
        </div>
        <button type="submit" disabled={isLoading} className="btn-metal mt-3 w-full">
          {isLoading ? (
            <>
              <span className="spinner" /> Creating account
            </>
          ) : (
            'Create account'
          )}
        </button>
      </form>
    </AuthShell>
  )
}
