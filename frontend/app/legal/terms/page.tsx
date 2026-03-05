import Link from "next/link";

export const metadata = {
    title: "Terms of Service – Fin-Eye",
    description: "Fin-Eye Terms of Service",
};

export default function TermsPage() {
    return (
        <div className="mx-auto max-w-3xl space-y-8 py-8 text-slate-300">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-50">Terms of Service</h1>
                <p className="mt-2 text-sm text-slate-500">Version 1.0.0 · Effective March 2026</p>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 text-sm text-amber-300">
                <strong>Important:</strong> Fin-Eye is an educational analytics platform. Nothing on this
                platform constitutes investment advice, a recommendation, or an offer to buy or sell any
                security. Always consult a licensed financial adviser before making any trading decisions.
            </div>

            <Section title="1. Acceptance of Terms">
                By accessing or using Fin-Eye you agree to be bound by these Terms of Service and our
                Privacy Policy. If you do not agree, please do not use the platform.
            </Section>

            <Section title="2. Nature of the Service">
                Fin-Eye provides educational market intelligence tools including algorithmic signal
                analysis, backtesting simulations, macro dashboards, and sentiment visualisations. All
                outputs are produced by statistical models trained on historical data and are provided
                solely for educational and informational purposes. They do not constitute financial,
                investment, tax, or legal advice.
            </Section>

            <Section title="3. No Investment Advice">
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    <li>Fin-Eye is not a registered investment adviser, broker-dealer, or financial planner.</li>
                    <li>No signal, score, or recommendation produced by the platform should be construed as advice to buy, sell, or hold any security.</li>
                    <li>Past model performance does not guarantee future results. Backtested returns will typically differ materially from live trading outcomes.</li>
                    <li>You are solely responsible for any financial decisions you make.</li>
                </ul>
            </Section>

            <Section title="4. Model Limitations & Overfitting Risk">
                Machine learning models are trained on historical data and may fail during regime changes,
                black-swan events, or periods outside their training distribution. Backtest results are
                subject to look-ahead bias, survivorship bias, and overfitting. The platform displays
                overfitting warnings when statistical thresholds are exceeded, but these warnings are not
                exhaustive. You acknowledge these limitations by using the service.
            </Section>

            <Section title="5. User Accounts & Security">
                You are responsible for maintaining the confidentiality of your account credentials. You
                agree to notify us immediately of any unauthorised use of your account. Fin-Eye will not be
                liable for any loss arising from your failure to secure your credentials.
            </Section>

            <Section title="6. Intellectual Property">
                All content, models, algorithms, design, and code on the platform are the intellectual
                property of Fin-Eye or its licensors. You receive a limited, non-exclusive, non-transferable
                licence to access and use the platform for personal, non-commercial purposes. You may not
                scrape, copy, redistribute, or commercialise any part of the platform without written
                permission.
            </Section>

            <Section title="7. Acceptable Use">
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    <li>You may not use the platform for any unlawful purpose.</li>
                    <li>You may not attempt to reverse-engineer, decompile, or extract our models or algorithms.</li>
                    <li>You may not use automated scripts, bots, or scrapers against the API without a written agreement.</li>
                    <li>You may not share your account or credentials with third parties.</li>
                </ul>
            </Section>

            <Section title="8. Subscriptions & Payments">
                Pro subscriptions are billed monthly or annually via Stripe. You may cancel at any time;
                access continues until the end of the billing period. Refunds are handled on a case-by-case
                basis within 14 days of initial purchase. We reserve the right to change pricing with 30
                days notice.
            </Section>

            <Section title="9. Limitation of Liability">
                To the maximum extent permitted by applicable law, Fin-Eye and its operators shall not be
                liable for any direct, indirect, incidental, special, or consequential damages arising from
                your use of the platform, including but not limited to trading losses, data inaccuracies,
                model errors, or service interruptions. The platform is provided "as is" without warranties
                of any kind.
            </Section>

            <Section title="10. Indemnification">
                You agree to indemnify and hold Fin-Eye harmless from any claims, damages, or expenses
                arising from your violation of these Terms, your use of the platform, or your trading
                activity.
            </Section>

            <Section title="11. Data & Privacy">
                Your use of the platform is governed by our{" "}
                <Link href="/legal/privacy" className="text-blue-400 underline hover:text-blue-300">
                    Privacy Policy
                </Link>
                . We collect minimal personal data (email, usage events) and do not sell your data to third
                parties.
            </Section>

            <Section title="12. Changes to Terms">
                We may update these Terms at any time. When we do, the version number and effective date
                will change. Continued use after changes constitutes acceptance. For material changes, we
                will require you to re-accept within the application.
            </Section>

            <Section title="13. Governing Law">
                These Terms are governed by and construed in accordance with applicable EU law. Any disputes
                shall be resolved through binding arbitration or the courts of the applicable jurisdiction.
            </Section>

            <Section title="14. Contact">
                For questions about these Terms, contact us at{" "}
                <span className="text-blue-400">legal@fin-eye.io</span>.
            </Section>

            <div className="border-t border-slate-800 pt-6 flex flex-wrap gap-4 text-sm">
                <Link href="/legal/privacy" className="text-blue-400 hover:text-blue-300">Privacy Policy</Link>
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
