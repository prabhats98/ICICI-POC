/**
 * LandingPage - Enterprise-grade landing page for CloudGuard platform.
 * All icons are inline SVGs — no emojis.
 */

import { useNavigate } from 'react-router-dom';
import Threads from '../components/Threads';
import {
  ShieldIcon, BrainIcon, BroadcastIcon, AlertIcon, ChartIcon,
  InboxIcon, SearchIcon, TagIcon, LinkIcon, FlaskIcon, MailIcon,
  LockIcon, GlobeIcon, CloudIcon, KeyIcon, ClipboardIcon,
  RocketIcon, ArrowRightIcon, ArrowDownIcon,
} from '../components/Icons';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="landing-nav" id="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-nav-brand">
            <img src="/image.png" alt="KR Elixir" className="landing-nav-logo" />
            <div>
              <div className="landing-nav-title">CloudGuard</div>
              <div className="landing-nav-subtitle">by KR Elixir Technology</div>
            </div>
          </div>
          <div className="landing-nav-links">
            <a href="#features" className="landing-nav-link">Features</a>
            <a href="#architecture" className="landing-nav-link">Architecture</a>
            <a href="#compliance" className="landing-nav-link">Compliance</a>
            <button className="btn btn-primary" id="nav-sign-in" onClick={() => navigate('/login')}>
              Sign In
            </button>
          </div>
        </div>
      </nav>

      {/* Hero — Threads animation background */}
      <section className="landing-hero" id="landing-hero">
        <div className="landing-hero-threads-bg">
          <Threads
            amplitude={1}
            distance={0}
            enableMouseInteraction={false}
            color={[0.39, 0.4, 0.95]}
          />
        </div>
        <div className="landing-hero-glow" />
        <div className="landing-hero-content">
          <div className="landing-hero-badge">
            <span className="landing-hero-badge-dot" />
            Powered by Azure AI &amp; Multi-Agent Architecture
          </div>
          <h1 className="landing-hero-title">
            Azure Cloud Log
            <br />
            <span className="landing-hero-gradient">Intelligence Platform</span>
          </h1>
          <p className="landing-hero-desc">
            AI-driven incident detection, analysis, and resolution for banking cloud infrastructure.
            Transform raw Azure logs into actionable intelligence with multi-agent AI pipeline.
          </p>
          <div className="landing-hero-actions">
            <button className="btn btn-primary btn-lg" id="hero-sign-in" onClick={() => navigate('/login')}>
              <ShieldIcon size={18} /> Access Dashboard
            </button>
            <a href="#features" className="btn btn-secondary btn-lg" id="hero-learn-more">
              Learn More <ArrowDownIcon size={14} />
            </a>
          </div>
          <div className="landing-hero-stats">
            <div className="landing-hero-stat">
              <span className="landing-hero-stat-value">98.7%</span>
              <span className="landing-hero-stat-label">Threat Accuracy</span>
            </div>
            <div className="landing-hero-stat-divider" />
            <div className="landing-hero-stat">
              <span className="landing-hero-stat-value">&lt;2min</span>
              <span className="landing-hero-stat-label">Detection Time</span>
            </div>
            <div className="landing-hero-stat-divider" />
            <div className="landing-hero-stat">
              <span className="landing-hero-stat-value">99.9%</span>
              <span className="landing-hero-stat-label">Uptime SLA</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features — no scroll animations */}
      <section className="landing-section" id="features">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-badge">CAPABILITIES</span>
            <h2 className="landing-section-title">Enterprise-Grade Cloud Security</h2>
            <p className="landing-section-desc">
              Purpose-built for banking infrastructure with AI-powered threat detection and automated incident response.
            </p>
          </div>
          <div className="landing-features-grid">
            {[
              { Icon: BrainIcon, title: 'AI-Powered Analysis', desc: 'Multi-agent Gemini AI pipeline processes logs through classification, correlation, and deep code analysis for root cause identification.', accent: 'indigo' },
              { Icon: BroadcastIcon, title: 'Real-Time Monitoring', desc: 'WebSocket-powered live pipeline visualization. Track every agent step with real-time I/O data and processing metrics.', accent: 'blue' },
              { Icon: AlertIcon, title: 'Incident Management', desc: 'Automated incident creation with P1/P2/P3 prioritization, resolution recommendations, and email alerting via Azure Communication Services.', accent: 'rose' },
              { Icon: ChartIcon, title: 'Compliance & Reporting', desc: 'Export-ready reports in JSON, CSV, and Excel formats. Audit trails and compliance documentation for SOC 2 and ISO 27001.', accent: 'emerald' },
            ].map((feature, i) => (
              <div key={i} className="landing-feature-card">
                <div className={`landing-feature-icon ${feature.accent}`}><feature.Icon size={26} /></div>
                <h3 className="landing-feature-title">{feature.title}</h3>
                <p className="landing-feature-desc">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture — no scroll animations */}
      <section className="landing-section landing-section-dark" id="architecture">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-badge">ARCHITECTURE</span>
            <h2 className="landing-section-title">Multi-Agent AI Pipeline</h2>
            <p className="landing-section-desc">
              Eight specialized AI agents work in sequence to transform raw Azure logs into resolved incidents.
            </p>
          </div>
          <div className="landing-pipeline">
            {[
              { Icon: InboxIcon, name: 'Ingestion', desc: 'Azure Monitor & Log Analytics' },
              { Icon: SearchIcon, name: 'Preprocessing', desc: 'Normalize & structure logs' },
              { Icon: TagIcon, name: 'Classification', desc: 'Gemini AI categorization' },
              { Icon: LinkIcon, name: 'Correlation', desc: 'Cross-log incident linking' },
              { Icon: FlaskIcon, name: 'Deep Analysis', desc: 'Root cause identification' },
              { Icon: MailIcon, name: 'Notification', desc: 'Alerts & email dispatch' },
            ].map((step, i) => (
              <div key={i} className="landing-pipeline-step">
                <div className="landing-pipeline-node">
                  <span className="landing-pipeline-icon"><step.Icon size={22} /></span>
                  <span className="landing-pipeline-name">{step.name}</span>
                  <span className="landing-pipeline-desc">{step.desc}</span>
                </div>
                {i < 5 && <div className="landing-pipeline-arrow"><ArrowRightIcon size={18} /></div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust / Compliance — no scroll animations */}
      <section className="landing-section" id="compliance">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-badge">TRUST & SECURITY</span>
            <h2 className="landing-section-title">Enterprise Security Standards</h2>
            <p className="landing-section-desc">
              Built with banking-grade security practices and compliance-ready architecture.
            </p>
          </div>
          <div className="landing-trust-grid">
            {[
              { Icon: LockIcon, title: 'SOC 2 Type II', desc: 'Compliant security controls and audit logging' },
              { Icon: GlobeIcon, title: 'ISO 27001', desc: 'Information security management certified' },
              { Icon: CloudIcon, title: 'Azure Native', desc: 'Fully integrated with Azure security services' },
              { Icon: KeyIcon, title: 'JWT Auth', desc: 'Secure token-based authentication' },
              { Icon: ClipboardIcon, title: 'Audit Trail', desc: 'Complete logging of all system actions' },
              { Icon: ShieldIcon, title: 'Data Encryption', desc: 'End-to-end encryption for data in transit and at rest' },
            ].map((item, i) => (
              <div key={i} className="landing-trust-card">
                <span className="landing-trust-icon"><item.Icon size={28} /></span>
                <h3 className="landing-trust-title">{item.title}</h3>
                <p className="landing-trust-desc">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA — no scroll animations */}
      <section className="landing-cta">
        <div className="landing-cta-inner">
          <h2 className="landing-cta-title">Ready to Secure Your Cloud?</h2>
          <p className="landing-cta-desc">
            Get started with CloudGuard's AI-powered log analysis platform for your banking infrastructure.
          </p>
          <button className="btn btn-primary btn-lg" id="cta-sign-in" onClick={() => navigate('/login')}>
            <RocketIcon size={18} /> Get Started
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer" id="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">
            <img src="/image.png" alt="KR Elixir" className="landing-footer-logo" />
            <div>
              <div className="landing-footer-name">CloudGuard</div>
              <div className="landing-footer-tagline">by KR Elixir Technology</div>
            </div>
          </div>
          <div className="landing-footer-copy">
            © {new Date().getFullYear()} KR Elixir Technology Pvt. Ltd. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
