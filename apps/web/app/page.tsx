"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type TeamProfile = {
  id: string;
  display_name: string;
  short_name: string;
  active: boolean;
  external_team_id: string | null;
  locale: string;
  fan_identity: string;
  profile_version: number;
};

type Fixture = {
  id: string;
  home_external_team_id: string;
  away_external_team_id: string;
  home_name: string;
  away_name: string;
  kickoff_at: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
};

type TeamMatchStat = {
  metric_code: string;
  metric_value: number;
  metric_unit: string;
  period: string;
};

type Baseline = {
  metric_code: string;
  window_type: string;
  sample_size: number;
  mean_value: number | null;
};

type Insight = {
  id: string;
  insight_type: string;
  claim: string;
  final_score: number;
  confidence_score: number;
  eligible: boolean;
  rejection_reason: string | null;
  selected: boolean;
};

type EditorialContext = {
  language: string;
  character: { locale: string; identity: string };
  emotion: { primary: string; secondary: string; intensity: number; rivalry: number };
  narrative_angle: { code: string; rationale: string };
  duration: { target_duration_seconds: number; target_word_count: number; minimum_word_count: number; maximum_word_count: number };
  ready_for_script: boolean;
  readiness_reason: string | null;
};

type GenerationJob = {
  id: string;
  content_type: string;
  status: string;
  scheduled_for: string;
  last_error: string | null;
};

type ContentPack = {
  id: string;
  team_profile_id: string;
  fixture_id: string;
  content_type: string;
  revision_number: number;
  revised_from_id: string | null;
  revision_reason: string | null;
  status: string;
  language: string;
  title: string | null;
  first_screen_text: string | null;
  script: string | null;
  recommended_hook: string | null;
  target_duration_seconds: number;
  target_word_count: number;
  quality_warning: boolean;
  hooks: { type?: string; text?: string }[];
  segments: { start?: number; end?: number; purpose?: string; text?: string; evidence_ids?: string[] }[];
  selected_insights: { id?: string; type?: string; claim?: string; final_score?: number }[];
  evidence_manifest: { evidence_id?: string; insight_id?: string; claim?: string; metric?: string; [key: string]: unknown }[];
  quality_checks: Record<string, unknown>;
  caption: string | null;
  comment_question: string | null;
  hashtags: string[];
  editorial_tags: Record<string, unknown>;
  review_note: string | null;
  created_at: string;
};

type ContentPerformance = {
  id: string;
  platform: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  average_percentage_viewed: number | null;
  measured_at: string;
  source: string;
};

type AdminUser = {
  id: string;
  email: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function HomePage() {
  const [teams, setTeams] = useState<TeamProfile[]>([]);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [selectedFixture, setSelectedFixture] = useState<Fixture | null>(null);
  const [selectedStats, setSelectedStats] = useState<TeamMatchStat[]>([]);
  const [selectedBaselines, setSelectedBaselines] = useState<Baseline[]>([]);
  const [selectedInsights, setSelectedInsights] = useState<Insight[]>([]);
  const [editorialContext, setEditorialContext] = useState<EditorialContext | null>(null);
  const [contentPack, setContentPack] = useState<ContentPack | null>(null);
  const [contents, setContents] = useState<ContentPack[]>([]);
  const [contentFilter, setContentFilter] = useState("NEEDS_REVIEW");
  const [user, setUser] = useState<AdminUser | null>(null);
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [editableScript, setEditableScript] = useState("");
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null);
  const [performances, setPerformances] = useState<ContentPerformance[]>([]);
  const [performancePlatform, setPerformancePlatform] = useState("tiktok");
  const [performanceViews, setPerformanceViews] = useState("0");
  const [performanceLikes, setPerformanceLikes] = useState("0");
  const [performanceComments, setPerformanceComments] = useState("0");
  const [performanceShares, setPerformanceShares] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadTeams = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${apiUrl}/teams`);
      if (!response.ok) throw new Error("Impossible de charger les profils d'équipe.");
      setTeams((await response.json()) as TeamProfile[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadFixtures = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/fixtures`);
      if (!response.ok) throw new Error("Impossible de charger les matchs.");
      setFixtures((await response.json()) as Fixture[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }, []);

  const loadJobs = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/jobs`);
      if (!response.ok) throw new Error("Impossible de charger les jobs.");
      setJobs((await response.json()) as GenerationJob[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }, []);

  const loadCurrentUser = useCallback(async () => {
    const response = await fetch(`${apiUrl}/auth/me`, { credentials: "include" });
    if (response.ok) setUser((await response.json()) as AdminUser);
    else setUser(null);
  }, []);

  const loadContents = useCallback(async (status = contentFilter) => {
    if (!user) return;
    try {
      const response = await fetch(`${apiUrl}/contents?status=${status}`, { credentials: "include" });
      if (!response.ok) throw new Error("Impossible de charger les contenus à revoir.");
      setContents((await response.json()) as ContentPack[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }, [contentFilter, user]);

  const loadPerformance = useCallback(async (contentId: string) => {
    try {
      const response = await fetch(`${apiUrl}/contents/${contentId}/performance`, { credentials: "include" });
      if (!response.ok) throw new Error("Impossible de charger les performances.");
      setPerformances((await response.json()) as ContentPerformance[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }, []);

  useEffect(() => {
    // The request synchronizes this client view with the API on first render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadTeams();
    void loadFixtures();
    void loadJobs();
    void loadCurrentUser();
  }, [loadCurrentUser, loadFixtures, loadJobs, loadTeams]);

  useEffect(() => {
    // The review queue is a server-backed view that follows the authenticated session and filter.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadContents();
  }, [loadContents]);

  async function syncTeam(teamId: string) {
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/teams/${teamId}/sync`, { method: "POST" });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Synchronisation impossible.");
      }
      await Promise.all([loadFixtures(), loadJobs()]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }

  async function createTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setIsSubmitting(true);
    setError(null);
    const payload = {
      slug: String(form.get("slug")),
      display_name: String(form.get("display_name")),
      short_name: String(form.get("short_name")),
      football_provider: String(form.get("football_provider")),
      external_team_id: String(form.get("external_team_id")) || null,
      timezone: String(form.get("timezone")),
      primary_script_language: String(form.get("primary_script_language")),
      locale: String(form.get("locale")),
      fan_identity: String(form.get("fan_identity")),
      character_description: String(form.get("character_description")) || null,
    };

    try {
      const response = await fetch(`${apiUrl}/teams`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Création impossible.");
      }
      event.currentTarget.reset();
      await loadTeams();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function inspectFixture(fixture: Fixture, refresh = false) {
    setError(null);
    setSelectedFixture(fixture);
    setEditorialContext(null);
    setContentPack(null);
    setPerformances([]);
    const linkedTeam = teams.find(
      (team) => team.external_team_id === fixture.home_external_team_id || team.external_team_id === fixture.away_external_team_id,
    );
    try {
      if (refresh) {
        const refreshResponse = await fetch(`${apiUrl}/fixtures/${fixture.id}/stats/refresh`, { method: "POST" });
        if (!refreshResponse.ok) throw new Error("Impossible de rafraîchir les statistiques.");
      }
      const teamQuery = linkedTeam ? `?team_id=${linkedTeam.id}` : "";
      const statsResponse = await fetch(`${apiUrl}/fixtures/${fixture.id}/stats${teamQuery}`);
      if (!statsResponse.ok) throw new Error("Impossible de charger les statistiques normalisées.");
      const stats = (await statsResponse.json()) as { team_stats: TeamMatchStat[] };
      setSelectedStats(stats.team_stats);
      if (linkedTeam) {
        const baselineResponse = await fetch(`${apiUrl}/fixtures/${fixture.id}/baselines?team_id=${linkedTeam.id}`);
        if (!baselineResponse.ok) throw new Error("Impossible de calculer les baselines.");
        setSelectedBaselines((await baselineResponse.json()) as Baseline[]);
        const insightsResponse = await fetch(`${apiUrl}/fixtures/${fixture.id}/insights?team_id=${linkedTeam.id}`);
        setSelectedInsights(insightsResponse.ok ? (await insightsResponse.json()) as Insight[] : []);
      } else {
        setSelectedBaselines([]);
        setSelectedInsights([]);
        setEditorialContext(null);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }

  async function recalculateInsights() {
    if (!selectedFixture) return;
    const linkedTeam = teams.find(
      (team) => team.external_team_id === selectedFixture.home_external_team_id || team.external_team_id === selectedFixture.away_external_team_id,
    );
    if (!linkedTeam) {
      setError("Aucun profil d'équipe lié à ce match.");
      return;
    }
    setError(null);
    try {
      const response = await fetch(
        `${apiUrl}/fixtures/${selectedFixture.id}/recalculate-insights?team_id=${linkedTeam.id}`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("Impossible de recalculer les insights.");
      setSelectedInsights((await response.json()) as Insight[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }

  async function buildEditorialContext() {
    if (!selectedFixture) return;
    const linkedTeam = teams.find(
      (team) => team.external_team_id === selectedFixture.home_external_team_id || team.external_team_id === selectedFixture.away_external_team_id,
    );
    if (!linkedTeam) {
      setError("Aucun profil d'équipe lié à ce match.");
      return;
    }
    setError(null);
    try {
      const response = await fetch(
        `${apiUrl}/fixtures/${selectedFixture.id}/editorial-context?team_id=${linkedTeam.id}`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("Impossible de préparer le contexte éditorial.");
      setEditorialContext((await response.json()) as EditorialContext);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }

  async function generateContent(contentType: "pre-match" | "post-match") {
    if (!selectedFixture) return;
    const linkedTeam = teams.find(
      (team) => team.external_team_id === selectedFixture.home_external_team_id || team.external_team_id === selectedFixture.away_external_team_id,
    );
    if (!linkedTeam) {
      setError("Aucun profil d'équipe lié à ce match.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(
        `${apiUrl}/fixtures/${selectedFixture.id}/generate/${contentType}?team_id=${linkedTeam.id}`,
        { method: "POST", credentials: "include" },
      );
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Génération impossible.");
      }
      const pack = (await response.json()) as ContentPack;
      setContentPack(pack);
      setEditableScript(pack.script ?? "");
      await loadPerformance(pack.id);
      await loadContents();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) throw new Error("Identifiants administrateur invalides.");
      setUser((await response.json()) as AdminUser);
      setPassword("");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function logout() {
    await fetch(`${apiUrl}/auth/logout`, { method: "POST", credentials: "include" });
    setUser(null);
    setContents([]);
    setContentPack(null);
  }

  async function selectContent(id: string) {
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/contents/${id}`, { credentials: "include" });
      if (!response.ok) throw new Error("Impossible de charger ce Content Pack.");
      const pack = (await response.json()) as ContentPack;
      setContentPack(pack);
      setEditableScript(pack.script ?? "");
      setSelectedInsightId(null);
      await loadPerformance(pack.id);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    }
  }

  async function reviewContent(action: "approve" | "reject" | "regenerate") {
    if (!contentPack) return;
    let body: Record<string, string> | undefined;
    if (action === "reject") {
      const reason = window.prompt("Motif de rejet :");
      if (!reason) return;
      body = { reason };
    }
    if (action === "approve") {
      const note = window.prompt("Note de validation (facultative) :");
      body = note ? { note } : {};
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/contents/${contentPack.id}/${action}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail ?? "Action de revue impossible.");
      }
      const pack = (await response.json()) as ContentPack;
      setContentPack(pack);
      setEditableScript(pack.script ?? "");
      await loadPerformance(pack.id);
      await loadContents();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function saveManualEdit() {
    if (!contentPack) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/contents/${contentPack.id}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script: editableScript, revision_reason: "MANUAL_REVIEW_EDIT" }),
      });
      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail ?? "Édition impossible : vérifier les preuves numériques.");
      }
      const pack = (await response.json()) as ContentPack;
      setContentPack(pack);
      setEditableScript(pack.script ?? "");
      await loadPerformance(pack.id);
      await loadContents();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function recordPerformance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contentPack) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/contents/${contentPack.id}/performance`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: performancePlatform,
          views: Number(performanceViews),
          likes: Number(performanceLikes),
          comments: Number(performanceComments),
          shares: Number(performanceShares),
        }),
      });
      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail ?? "Mesure impossible.");
      }
      await loadPerformance(contentPack.id);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <header>
        <p className="eyebrow">Football AI Fan Intelligence</p>
        <h1>Profils d&apos;équipe</h1>
        <p>Chaque équipe est une configuration indépendante du moteur.</p>
        {user ? (
          <p className="muted">Session administrateur : {user.email} <button type="button" onClick={() => void logout()}>Se déconnecter</button></p>
        ) : (
          <form className="login-form" onSubmit={login}>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <label>Mot de passe<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} /></label>
            <button type="submit" disabled={isSubmitting}>Connexion admin</button>
          </form>
        )}
      </header>

      <section aria-labelledby="team-list-title">
        <div className="section-heading">
          <h2 id="team-list-title">Équipes configurées</h2>
          <button type="button" onClick={() => void loadTeams()} disabled={isLoading}>Actualiser</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {isLoading ? <p>Chargement…</p> : (
          <ul className="team-grid">
            {teams.map((team) => (
              <li key={team.id}>
                <span className={team.active ? "status active" : "status"}>{team.active ? "Actif" : "Inactif"}</span>
                <h3>{team.display_name}</h3>
                <p>{team.short_name} · {team.locale} · v{team.profile_version}</p>
                <p className="muted">{team.fan_identity}</p>
                <button
                  type="button"
                  onClick={() => void syncTeam(team.id)}
                  disabled={!team.external_team_id}
                >
                  Synchroniser les matchs
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="fixtures-panel" aria-labelledby="fixture-list-title">
        <h2 id="fixture-list-title">Matchs synchronisés</h2>
        {fixtures.length === 0 ? <p>Aucun match en cache pour le moment.</p> : (
          <ul className="fixture-list">
            {fixtures.map((fixture) => (
              <li key={fixture.id}>
                <strong>{fixture.home_name} — {fixture.away_name}</strong>
                <span>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(fixture.kickoff_at))}</span>
                <span>{fixture.status}</span>
                {fixture.home_score !== null && fixture.away_score !== null && (
                  <strong>{fixture.home_score}–{fixture.away_score}</strong>
                )}
                <button type="button" onClick={() => void inspectFixture(fixture)}>Données</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {selectedFixture && (
        <section className="stats-panel" aria-labelledby="stats-title">
          <div className="section-heading">
            <div>
              <h2 id="stats-title">Données vérifiables — {selectedFixture.home_name} / {selectedFixture.away_name}</h2>
              <p className="muted">Valeurs fournisseur normalisées et baselines déterministes ; aucune donnée n&apos;est générée.</p>
            </div>
            <button type="button" onClick={() => void inspectFixture(selectedFixture, true)}>Rafraîchir les stats</button>
          </div>
          {selectedStats.length === 0 ? <p>Aucune statistique normalisée disponible.</p> : (
            <ul className="metric-list">
              {selectedStats.map((stat) => (
                <li key={`${stat.metric_code}-${stat.period}`}><strong>{stat.metric_code}</strong><span>{stat.metric_value} {stat.metric_unit}</span></li>
              ))}
            </ul>
          )}
          <h3>Baselines historiques</h3>
          {selectedBaselines.length === 0 ? <p>Pas assez d&apos;historique pour cette équipe ou ce match.</p> : (
            <ul className="metric-list">
              {selectedBaselines.filter((baseline) => baseline.window_type !== "LAST_10").map((baseline) => (
                <li key={`${baseline.metric_code}-${baseline.window_type}`}><strong>{baseline.metric_code} · {baseline.window_type}</strong><span>{baseline.mean_value ?? "—"} ({baseline.sample_size} matchs)</span></li>
              ))}
            </ul>
          )}
          <div className="section-heading insights-heading">
            <h3>Insights analytiques</h3>
            <button type="button" onClick={() => void recalculateInsights()}>Recalculer les insights</button>
          </div>
          {selectedInsights.length === 0 ? <p>Aucun insight calculé pour le moment.</p> : (
            <ul className="insight-list">
              {selectedInsights.map((insight) => (
                <li key={insight.id} className={insight.selected ? "selected" : ""}>
                  <strong>{insight.insight_type} · {insight.final_score}/100</strong>
                  <p>{insight.claim}</p>
                  <span className="muted">
                    {insight.eligible ? `Sélectionnable · confiance ${Math.round(insight.confidence_score * 100)}%` : `Exclu : ${insight.rejection_reason}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="section-heading editorial-heading">
            <h3>Package prêt pour le scénariste</h3>
            <button type="button" onClick={() => void buildEditorialContext()}>Préparer le contexte</button>
          </div>
          {editorialContext && (
            <div className="editorial-context">
              <p><strong>{editorialContext.ready_for_script ? "Prêt" : "Incomplet"}</strong> · {editorialContext.character.locale} · {editorialContext.language}</p>
              <p>Émotion : {editorialContext.emotion.primary} / {editorialContext.emotion.secondary} ({editorialContext.emotion.intensity}/100)</p>
              <p>Angle : {editorialContext.narrative_angle.code}</p>
              <p>Durée : {editorialContext.duration.target_duration_seconds}s · {editorialContext.duration.target_word_count} mots ({editorialContext.duration.minimum_word_count}–{editorialContext.duration.maximum_word_count})</p>
              {!editorialContext.ready_for_script && <p className="muted">{editorialContext.readiness_reason}</p>}
            </div>
          )}
          <div className="section-heading editorial-heading">
            <h3>Génération factuelle</h3>
            <div>
              <button type="button" onClick={() => void generateContent("pre-match")} disabled={isSubmitting}>Générer PRE_MATCH</button>
              <button type="button" onClick={() => void generateContent("post-match")} disabled={isSubmitting}>Générer POST_MATCH</button>
            </div>
          </div>
          <p className="muted">Le script reste systématiquement en attente de validation humaine.</p>
          {contentPack && (
            <div className="editorial-context">
              <p><strong>{contentPack.status}</strong> · {contentPack.language} · {contentPack.target_duration_seconds}s / {contentPack.target_word_count} mots</p>
              <p><strong>{contentPack.title}</strong></p>
              {contentPack.recommended_hook && <p>Hook : {contentPack.recommended_hook}</p>}
              {contentPack.script && <p>{contentPack.script}</p>}
              <p className="muted">{contentPack.evidence_manifest.length} preuves jointes{contentPack.quality_warning ? " · avertissement qualité" : ""}</p>
            </div>
          )}
        </section>
      )}

      {user && (
        <section className="review-panel" aria-labelledby="review-title">
          <div className="section-heading">
            <div>
              <h2 id="review-title">Validation humaine des contenus</h2>
              <p className="muted">Toute approbation, édition ou régénération conserve une trace et une révision.</p>
            </div>
            <label>État
              <select value={contentFilter} onChange={(event) => setContentFilter(event.target.value)}>
                <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                <option value="APPROVED">APPROVED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </label>
          </div>
          {contents.length === 0 ? <p>Aucun Content Pack dans cette file.</p> : (
            <ul className="insight-list">
              {contents.map((content) => (
                <li key={content.id} className={contentPack?.id === content.id ? "selected" : ""}>
                  <button type="button" onClick={() => void selectContent(content.id)}>
                    <strong>{content.status} · {content.content_type} · révision {content.revision_number}</strong>
                    <span>{content.title ?? "Sans titre"} · {content.language} · {new Date(content.created_at).toLocaleString("fr-FR")}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {contentPack && (
            <article className="editorial-context" aria-label="Détail du Content Pack">
              <h3>{contentPack.title ?? "Content Pack"}</h3>
              <p><strong>{contentPack.status}</strong> · {contentPack.content_type} · révision {contentPack.revision_number} · {contentPack.target_duration_seconds}s / {contentPack.target_word_count} mots</p>
              {contentPack.revision_reason && <p className="muted">Origine : {contentPack.revision_reason}</p>}
              {contentPack.quality_warning && <p className="error">Avertissement qualité : vérifiez les contrôles avant validation.</p>}
              {contentPack.review_note && <p className="muted">Note de revue : {contentPack.review_note}</p>}
              <h4>Hooks</h4>
              <ul>{contentPack.hooks.map((hook, index) => <li key={`${hook.type}-${index}`}><strong>{hook.type}</strong> — {hook.text}</li>)}</ul>
              <h4>Script</h4>
              <textarea aria-label="Script à éditer" rows={8} value={editableScript} onChange={(event) => setEditableScript(event.target.value)} />
              <div className="section-heading">
                <button type="button" onClick={() => void saveManualEdit()} disabled={isSubmitting}>Créer une révision éditée</button>
                <button type="button" onClick={() => void reviewContent("regenerate")} disabled={isSubmitting}>Régénérer</button>
                {contentPack.status === "NEEDS_REVIEW" && <>
                  <button type="button" onClick={() => void reviewContent("approve")} disabled={isSubmitting}>Approuver</button>
                  <button type="button" onClick={() => void reviewContent("reject")} disabled={isSubmitting}>Rejeter</button>
                </>}
              </div>
              <h4>Segments</h4>
              <ul>{contentPack.segments.map((segment, index) => <li key={`${segment.purpose}-${index}`}>{segment.start}s–{segment.end}s · <strong>{segment.purpose}</strong> — {segment.text}</li>)}</ul>
              <h4>Insights et preuves</h4>
              <ul className="insight-list">
                {contentPack.selected_insights.map((insight) => (
                  <li key={insight.id}>
                    <button type="button" onClick={() => setSelectedInsightId(insight.id ?? null)}><strong>{insight.type}</strong> — {insight.claim}</button>
                  </li>
                ))}
              </ul>
              <p className="muted">Cliquez sur un insight pour isoler ses preuves.</p>
              <ul className="metric-list">
                {contentPack.evidence_manifest.filter((evidence) => !selectedInsightId || evidence.insight_id === selectedInsightId).map((evidence) => (
                  <li key={evidence.evidence_id}><strong>{evidence.evidence_id} · {evidence.metric ?? "preuve"}</strong><span>{evidence.claim}<br />{JSON.stringify(evidence)}</span></li>
                ))}
              </ul>
              <details><summary>Contrôles qualité</summary><pre>{JSON.stringify(contentPack.quality_checks, null, 2)}</pre></details>
              <details><summary>Tags éditoriaux enregistrés</summary><pre>{JSON.stringify(contentPack.editorial_tags, null, 2)}</pre></details>
              <h4>Mesures de performance</h4>
              <p className="muted">Saisie manuelle uniquement en V1 ; aucune métrique ne modifie les faits ou le script.</p>
              <form onSubmit={recordPerformance}>
                <label>Plateforme<input value={performancePlatform} onChange={(event) => setPerformancePlatform(event.target.value)} required /></label>
                <label>Vues<input type="number" min="0" value={performanceViews} onChange={(event) => setPerformanceViews(event.target.value)} required /></label>
                <label>Likes<input type="number" min="0" value={performanceLikes} onChange={(event) => setPerformanceLikes(event.target.value)} required /></label>
                <label>Commentaires<input type="number" min="0" value={performanceComments} onChange={(event) => setPerformanceComments(event.target.value)} required /></label>
                <label>Partages<input type="number" min="0" value={performanceShares} onChange={(event) => setPerformanceShares(event.target.value)} required /></label>
                <button type="submit" disabled={isSubmitting}>Enregistrer la mesure</button>
              </form>
              {performances.length === 0 ? <p>Aucune mesure enregistrée.</p> : (
                <ul className="metric-list">
                  {performances.map((performance) => (
                    <li key={performance.id}>
                      <strong>{performance.platform} · {new Date(performance.measured_at).toLocaleString("fr-FR")}</strong>
                      <span>{performance.views} vues · {performance.likes} likes · {performance.comments} commentaires · {performance.shares} partages</span>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          )}
        </section>
      )}

      <section className="jobs-panel" aria-labelledby="job-list-title">
        <h2 id="job-list-title">Générations planifiées</h2>
        {jobs.length === 0 ? <p>Aucun job planifié.</p> : (
          <ul className="job-list">
            {jobs.map((job) => (
              <li key={job.id}>
                <strong>{job.content_type}</strong>
                <span className={`job-status ${job.status.toLowerCase()}`}>{job.status}</span>
                <span>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(job.scheduled_for))}</span>
                {job.last_error && <span className="muted">{job.last_error}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="create-panel" aria-labelledby="create-team-title">
        <h2 id="create-team-title">Créer une équipe</h2>
        <p>Par exemple, créez Real Madrid sans toucher au code.</p>
        <form onSubmit={createTeam}>
          <label>Slug<input name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="real-madrid" /></label>
          <label>Nom affiché<input name="display_name" required placeholder="Real Madrid" /></label>
          <label>Nom court<input name="short_name" required placeholder="Real Madrid" /></label>
          <label>Provider<input name="football_provider" defaultValue="sportmonks" required /></label>
          <label>ID équipe provider<input name="external_team_id" placeholder="à configurer" /></label>
          <label>Fuseau horaire<input name="timezone" defaultValue="Europe/Madrid" required /></label>
          <label>Langue du script<input name="primary_script_language" defaultValue="es" required /></label>
          <label>Locale<input name="locale" defaultValue="es-ES" required /></label>
          <label>Identité supporter<input name="fan_identity" required placeholder="native_madrid_supporter" /></label>
          <label className="wide">Description du personnage<textarea name="character_description" rows={3} /></label>
          <button className="primary" type="submit" disabled={isSubmitting}>{isSubmitting ? "Création…" : "Créer le profil"}</button>
        </form>
      </section>
    </main>
  );
}
