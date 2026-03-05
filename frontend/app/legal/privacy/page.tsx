import Link from "next/link";

export const metadata = {
    title: "Privacy Policy – Fin-Eye",
    description: "Fin-Eye Privacy Policy",
};

export default function PrivacyPage() {
    return (
        <div className="mx-auto max-w-3xl space-y-8 py-8 text-slate-300">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-50">Privacy Policy</h1>
                <p className="mt-2 text-sm text-slate-500">Version 1.0.0 · Effective March 2026</p>
            </div>

            <div className="rounded-xl border border-blue-500/20 bg-blue-950/10 p-4 text-sm text-blue-300">
                We believe in minimal data collection. We collect only what is necessary to operate the
                service, never sell your data, and respect your right to access and delete your information.
            </div>

            <Section title="1. Who We Are">
                Fin-Eye is an educational market intelligence platform. References to "we", "us", or "our"
                in this policy refer to the Fin-Eye platform and its operators.
            </Section>

            <Section title="2. What Data We Collect">
                <p className="mb-2">We collect the following categories of data:</p>
                <ul className="list-disc space-y-2 pl-5 text-sm">
                    <li>
                        <strong className="text-slate-200">Account data:</strong> Your email address and
                        hashed password (never stored in plaintext). Optionally, a display name.
                    </li>
                    <li>
                        <strong className="text-slate-200">Usage data:</strong> Which features you use,
                        pages visited, and general interaction patterns — used to improve the product.
                    </li>
                    <li>
                        <strong className="text-slate-200">Watchlist & portfolio data:</strong> Tickers and
                        portfolio allocations you explicitly save to the platform.
                    </li>
                    <li>
                        <strong className="text-slate-200">Consent records:</strong> Timestamps of when
                        you accepted the Terms of Service, for legal compliance.
                    </li>
                    <li>
                        <strong className="text-slate-200">Payment data:</strong> Handled entirely by
                        Stripe. We store only your subscription tier and renewal date — no card numbers,
                        CVVs, or banking information are stored on our servers.
                    </li>
                    <li>
                        <strong className="text-slate-200">Technical data:</strong> IP address, browser
                        type, and device type for security and abuse prevention. Retained for 30 days.
                    </li>
                </ul>
            </Section>

            <Section title="3. How We Use Your Data">
                <ul className="list-disc space-y-1 pl-5 text-sm">
                    <li>To create and manage your account.</li>
                    <li>To provide personalised watchlists, portfolios, and saved strategies.</li>
                    <li>To send transactional emails (signup confirmation, password reset, billing receipts).</li>
                    <li>To send optional marketing emails and weekly digests — only with your explicit consent.</li>
                    <li>To detect fraud, abuse, and security incidents.</li>
                    <li>To improve the platform based on aggregate usage patterns.</li>
                    <li>To comply with legal obligations.</li>
                </ul>
            </Section>

            <Section title="4. Data Sharing">
                We do not sell your personal data. We share data only with:
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    <li><strong className="text-slate-200">Stripe</strong> — Payment processing. Subject to Stripe's Privacy Policy.</li>
                    <li><strong className="text-slate-200">Cloud infrastructure providers</strong> (e.g. AWS) — Hosting and database. Covered by DPAs.</li>
                    <li><strong className="text-slate-200">Analytics tools</strong> (e.g. Plausible/Mixpanel) — Aggregated, privacy-respecting usage analytics only.</li>
                    <li><strong className="text-slate-200">Law enforcement</strong> — Only when legally required and only to the extent required.</li>
                </ul>
            </Section>

            <Section title="5. Cookies & Tracking">
                We use strictly necessary cookies for session management. We do not use third-party
                advertising cookies. Analytics cookies, if used, are privacy-preserving (no cross-site
                tracking). You may disable cookies in your browser, though some features may not work
                correctly.
            </Section>

            <Section title="6. Data Retention">
                <ul className="list-disc space-y-1 pl-5 text-sm">
                    <li>Account data: Retained while your account is active, deleted within 30 days of account deletion request.</li>
                    <li>Usage logs: Retained for 90 days for security purposes.</li>
                    <li>Technical logs: Retained for 30 days.</li>
                    <li>Backtest results and strategies: Retained until you delete them or close your account.</li>
                    <li>Consent records: Retained for legal compliance even after account deletion.</li>
                </ul>
            </Section>

            <Section title="7. Your Rights (GDPR & Applicable Law)">
                If you are located in the EU or UK, you have the following rights:
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    <li><strong className="text-slate-200">Right of access:</strong> Request a copy of your personal data.</li>
                    <li><strong className="text-slate-200">Right to rectification:</strong> Correct inaccurate data.</li>
                    <li><strong className="text-slate-200">Right to erasure:</strong> Request deletion of your account and personal data.</li>
                    <li><strong className="text-slate-200">Right to restriction:</strong> Limit how we process your data.</li>
                    <li><strong className="text-slate-200">Right to portability:</strong> Receive your data in a machine-readable format.</li>
                    <li><strong className="text-slate-200">Right to object:</strong> Object to marketing communications at any time.</li>
                </ul>
                <p className="mt-2">
                    To exercise any of these rights, contact us at{" "}
                    <span className="text-blue-400">privacy@fin-eye.io</span>. We will respond within 30 days.
                    Data export and deletion requests can also be initiated from the Settings page (coming soon).
                </p>
            </Section>

            <Section title="8. Security">
                We use industry-standard security measures: HTTPS/TLS encryption in transit, encrypted
                databases at rest, bcrypt password hashing, and regular security reviews. We maintain an
                incident response plan and will notify affected users within 72 hours of a confirmed data
                breach.
            </Section>

            <Section title="9. Children">
                Fin-Eye is not intended for users under the age of 18. We do not knowingly collect data
                from minors. If you believe a minor has registered, please contact us and we will delete
                the account promptly.
            </Section>

            <Section title="10. Changes to This Policy">
                We may update this policy periodically. The version number and effective date at the top
                of this page will reflect any changes. For material changes, we will notify you via email
                or an in-app notice and, where required, request re-consent.
            </Section>

            <Section title="11. Contact">
                <p>For privacy enquiries: <span className="text-blue-400">privacy@fin-eye.io</span></p>
            </Section>

            <div className="border-t border-slate-800 pt-6 flex flex-wrap gap-4 text-sm">
                <Link href="/legal/terms" className="text-blue-400 hover:text-blue-300">Terms of Service</Link>
                <Link href="/legal/disclaimer" className="text-blue-400 hover:text-blue-300">Risk Disclaimer</Link>
                <Link href="/" className="text-slate-500 hover:text-slate-400">← Back to App</Link>
            </div>
        </div>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
            <div className="text-sm leading-relaxed text-slate-400">{children}</div>
        </section>
    );
}
