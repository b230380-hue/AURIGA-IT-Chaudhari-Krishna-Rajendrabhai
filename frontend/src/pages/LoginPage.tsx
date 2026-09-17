import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, User, Lock, Mail, AlertCircle, ArrowRight, UserCheck } from 'lucide-react';

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('PHARMACIST');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(username, email, password, role);
      } else {
        await login(username, password);
      }
      navigate('/');
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || 'Authentication failed. Please check credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (u: string, p: string) => {
    setIsRegister(false);
    setUsername(u);
    setPassword(p);
    setError('');
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-secondary)',
      padding: '1.5rem',
    }}>
      <div className="card" style={{ maxWidth: '440px', width: '100%', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'var(--primary-color)',
            color: 'white',
            marginBottom: '0.75rem',
          }}>
            <ShieldCheck size={28} />
          </div>
          <h2 style={{ margin: 0, fontSize: '1.5rem' }}>PharmaFlow</h2>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            {isRegister ? 'Create staff or admin account' : 'Sign in to pharmacy management console'}
          </p>
        </div>

        {/* Demo Quick-Fill Buttons */}
        {!isRegister && (
          <div style={{
            background: '#f8fafc',
            border: '1px dashed var(--border-color)',
            borderRadius: '8px',
            padding: '0.75rem',
            marginBottom: '1.25rem',
          }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              QUICK DEMO SIGN-IN:
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: '0.8rem', padding: '0.4rem' }}
                onClick={() => fillDemo('admin', 'admin123')}
              >
                <UserCheck size={14} />
                Admin (Full Access)
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: '0.8rem', padding: '0.4rem' }}
                onClick={() => fillDemo('pharmacist', 'pharma123')}
              >
                <User size={14} />
                Pharmacist
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1.25rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.875rem', fontWeight: 500 }}>
              Username
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. admin or pharmacist"
                style={{ paddingLeft: '2.25rem', width: '100%' }}
              />
              <User size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            </div>
          </div>

          {isRegister && (
            <>
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.875rem', fontWeight: 500 }}>
                  Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="email"
                    className="input"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@pharmacy.local"
                    style={{ paddingLeft: '2.25rem', width: '100%' }}
                  />
                  <Mail size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.875rem', fontWeight: 500 }}>
                  Role
                </label>
                <select
                  className="input"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="PHARMACIST">Pharmacist (Dispensing & Stock)</option>
                  <option value="ADMIN">Administrator (Full Access & Automation)</option>
                </select>
              </div>
            </>
          )}

          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.875rem', fontWeight: 500 }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="input"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                style={{ paddingLeft: '2.25rem', width: '100%' }}
              />
              <Lock size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem', justifyContent: 'center' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.875rem' }}>
          {isRegister ? (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegister(false); setError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', fontWeight: 600 }}
              >
                Sign In
              </button>
            </span>
          ) : (
            <span>
              Need a new account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegister(true); setError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', fontWeight: 600 }}
              >
                Register
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
