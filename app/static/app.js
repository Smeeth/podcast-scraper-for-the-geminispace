// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

'use strict';

const app = {
  state: {
    podcasts: [],
    activePodcast: null,
    activeEpisode: null,
    currentProbe: null,
    filterQuery: '',
    archiveQuery: '',
    isScraping: false
  },

  init: function () {
    this.bindEvents();
    this.checkHealth();
    this.fetchArchive();
  },

  bindEvents: function () {
    // Scraper Form (Stufe 1: Probe)
    const scrapeForm = document.getElementById('scrapeForm');
    if (scrapeForm) {
      scrapeForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleProbe();
      });
    }

    // URL Platform Auto-Detection
    const urlInput = document.getElementById('mediaUrlInput');
    if (urlInput) {
      urlInput.addEventListener('input', (e) => this.handleUrlInput(e.target.value));
    }

    // Episode Filter
    const epFilter = document.getElementById('episodeFilterInput');
    if (epFilter) {
      epFilter.addEventListener('input', (e) => {
        this.state.filterQuery = e.target.value.toLowerCase().trim();
        this.renderEpisodesTable();
      });
    }

    // Archive Filter
    const archFilter = document.getElementById('archiveSearchInput');
    if (archFilter) {
      archFilter.addEventListener('input', (e) => {
        this.state.archiveQuery = e.target.value.toLowerCase().trim();
        this.renderArchiveList();
      });
    }

    // AI Lab Buttons
    document.getElementById('genSummaryBtn')?.addEventListener('click', () => this.runAIAnalysis('summary'));
    document.getElementById('genGuestsBtn')?.addEventListener('click', () => this.runAIAnalysis('guests_topics'));

    document.getElementById('qaForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = document.getElementById('qaInput')?.value;
      if (query) this.runAIAnalysis('qa', query);
    });

    document.getElementById('chatForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = document.getElementById('chatInput')?.value;
      if (query) this.runAIAnalysis('custom_chat', query);
    });

    // Delete Podcast Button
    document.getElementById('deleteActivePodcastBtn')?.addEventListener('click', () => {
      if (this.state.activePodcast) {
        if (confirm(`Möchtest du "${this.state.activePodcast.title}" wirklich aus dem Archiv löschen?`)) {
          this.deletePodcast(this.state.activePodcast.id);
        }
      }
    });

    // Drawer Fetch Transcript Button
    document.getElementById('drawerFetchTranscriptBtn')?.addEventListener('click', () => {
      if (this.state.activeEpisode) {
        this.fetchEpisodeTranscript(this.state.activeEpisode.id);
      }
    });

    // Backdrop click
    document.getElementById('drawerBackdrop')?.addEventListener('click', () => this.closeDrawer());
  },


  // ===========================================================================
  // System & Health Check
  // ===========================================================================
  checkHealth: async function () {
    try {
      const resp = await fetch('/api/health');
      if (!resp.ok) throw new Error('Health check failed');
      const data = await resp.json();

      const geminiBadge = document.getElementById('geminiStatusBadge');
      if (geminiBadge) {
        if (data.gemini_available) {
          geminiBadge.className = 'badge bg-success';
          geminiBadge.textContent = `Gemini AI (${data.gemini_model})`;
        } else {
          geminiBadge.className = 'badge bg-warning text-dark';
          geminiBadge.textContent = 'Gemini AI: Key fehlt (.env)';
        }
      }

      const dbBadge = document.getElementById('dbStatusBadge');
      if (dbBadge) {
        if (data.database === 'healthy') {
          dbBadge.className = 'badge bg-info';
          dbBadge.textContent = 'PostgreSQL: Online';
        } else {
          dbBadge.className = 'badge bg-danger';
          dbBadge.textContent = 'DB: Offline';
        }
      }
    } catch (err) {
      console.warn('Health check error:', err);
    }
  },

  // ===========================================================================
  // Scraper Ingestion
  // ===========================================================================
  handleUrlInput: function (url) {
    const badge = document.getElementById('urlPlatformDetectBadge');
    if (!badge) return;
    const lower = url.toLowerCase().trim();

    if (lower.includes('youtube.com') || lower.includes('youtu.be')) {
      badge.className = 'badge badge-youtube d-inline-block';
      badge.textContent = '▶️ YouTube Feed';
    } else if (lower.includes('podcasts.apple.com')) {
      badge.className = 'badge badge-apple d-inline-block';
      badge.textContent = '🍏 Apple Podcasts';
    } else if (lower.startsWith('http://') || lower.startsWith('https://')) {
      badge.className = 'badge badge-rss d-inline-block';
      badge.textContent = '🎙️ RSS / Atom Feed';
    } else {
      badge.className = 'badge bg-secondary d-none';
    }
  },

  handleProbe: async function () {
    const urlInput = document.getElementById('mediaUrlInput');
    const submitBtn = document.getElementById('scrapeSubmitBtn');
    const spinner = document.getElementById('scrapeSpinner');
    const btnText = document.getElementById('scrapeBtnText');
    const probeCard = document.getElementById('probePreviewCard');

    const url = urlInput?.value.trim();
    if (!url) return;

    // UI Loading State
    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    if (btnText) btnText.textContent = 'Prüfe...';

    try {
      const resp = await fetch('/api/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Kanal konnte nicht vorab geprüft werden.');
      }

      this.state.currentProbe = data;

      // Populate preview card
      const titleEl = document.getElementById('probeTitle');
      const authorEl = document.getElementById('probeAuthor');
      const descEl = document.getElementById('probeDescription');
      const imgEl = document.getElementById('probeImage');
      const platformBadge = document.getElementById('probePlatformBadge');
      const countBadge = document.getElementById('probeCountBadge');

      if (titleEl) titleEl.textContent = data.title;
      if (authorEl) authorEl.textContent = data.author || 'Unbekannt';
      if (descEl) descEl.textContent = data.description || 'Keine Beschreibung angegeben.';
      if (imgEl && data.image_url) imgEl.src = data.image_url;

      if (platformBadge) {
        platformBadge.textContent = data.platform.toUpperCase();
        platformBadge.className = data.platform === 'youtube' ? 'badge badge-youtube' : (data.platform === 'apple' ? 'badge badge-apple' : 'badge badge-rss');
      }

      if (countBadge) {
        countBadge.textContent = data.approx_episodes_count ? `ca. ${data.approx_episodes_count} Folgen verfügbar` : 'Kanal bereit';
      }

      if (probeCard) probeCard.classList.remove('d-none');
      this.showToast(`Kanal erkannt: "${data.title}"`, 'info');
    } catch (err) {
      this.showToast(err.message, 'danger');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      if (spinner) spinner.classList.add('d-none');
      if (btnText) btnText.textContent = '🔍 Vorab prüfen';
    }
  },

  cancelProbe: function () {
    const probeCard = document.getElementById('probePreviewCard');
    if (probeCard) probeCard.classList.add('d-none');
    this.state.currentProbe = null;
  },

  confirmDeepScan: async function () {
    const probeData = this.state.currentProbe;
    if (!probeData) return;

    const limitSelect = document.getElementById('probeLimitSelect');
    const fetchTransCheck = document.getElementById('probeFetchTranscriptsCheck');
    const confirmBtn = document.getElementById('probeConfirmBtn');
    const spinner = document.getElementById('probeDeepScanSpinner');
    const progBar = document.getElementById('scrapeProgressBarContainer');

    const limit = parseInt(limitSelect?.value || '50', 10);
    const fetchTranscripts = !!fetchTransCheck?.checked;

    if (confirmBtn) confirmBtn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    if (progBar) progBar.classList.remove('d-none');

    try {
      const resp = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: probeData.url, limit, fetch_transcripts: fetchTranscripts })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Fehler beim Tiefenscan.');
      }

      this.showToast(`Tiefenscan abgeschlossen: "${data.title}" (${data.episodes.length} Folgen)`, 'success');
      this.cancelProbe();
      const urlInput = document.getElementById('mediaUrlInput');
      if (urlInput) urlInput.value = '';
      await this.fetchArchive();
      await this.selectPodcast(data.id);
    } catch (err) {
      this.showToast(err.message, 'danger');
    } finally {
      if (confirmBtn) confirmBtn.disabled = false;
      if (spinner) spinner.classList.add('d-none');
      if (progBar) progBar.classList.add('d-none');
    }
  },


  // ===========================================================================
  // Archive Management
  // ===========================================================================
  fetchArchive: async function () {
    try {
      const resp = await fetch('/api/podcasts');
      if (!resp.ok) throw new Error('Konnte Archiv nicht laden');
      this.state.podcasts = await resp.json();
      this.renderArchiveList();

      // Badge Update
      const countBadge = document.getElementById('archiveCountBadge');
      if (countBadge) countBadge.textContent = this.state.podcasts.length;

      // Wenn noch kein aktiver Podcast gewählt ist und Podcasts vorhanden sind, den ersten wählen
      if (!this.state.activePodcast && this.state.podcasts.length > 0) {
        this.selectPodcast(this.state.podcasts[0].id);
      }
    } catch (err) {
      console.error('Fehler beim Laden des Archivs:', err);
    }
  },

  renderArchiveList: function () {
    const list = document.getElementById('archiveList');
    if (!list) return;
    list.innerHTML = '';

    const filtered = this.state.podcasts.filter(p => {
      if (!this.state.archiveQuery) return true;
      return (p.title || '').toLowerCase().includes(this.state.archiveQuery) ||
        (p.author || '').toLowerCase().includes(this.state.archiveQuery);
    });

    if (filtered.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'text-center text-muted p-3 small';
      empty.textContent = this.state.archiveQuery ? 'Keine Treffer im Archiv.' : 'Noch keine Feeds im Archiv.';
      list.appendChild(empty);
      return;
    }

    filtered.forEach(p => {
      const item = document.createElement('div');
      const isActive = this.state.activePodcast && this.state.activePodcast.id === p.id;
      item.className = `archive-item ${isActive ? 'active' : ''}`;

      let platformBadge = '<span class="badge bg-secondary">RSS</span>';
      if (p.platform === 'youtube') platformBadge = '<span class="badge badge-youtube">YT</span>';
      if (p.platform === 'apple') platformBadge = '<span class="badge badge-apple">Apple</span>';

      item.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-1">
          <div class="fw-bold small text-truncate" style="max-width: 140px;" title="${this.escapeHtml(p.title)}">
            ${this.escapeHtml(p.title)}
          </div>
          ${platformBadge}
        </div>
        <div class="d-flex justify-content-between align-items-center text-muted" style="font-size: 0.75rem;">
          <span class="text-truncate" style="max-width: 110px;">${this.escapeHtml(p.author || 'Unbekannt')}</span>
          <span>${p.episode_count} Folgen</span>
        </div>
      `;

      item.addEventListener('click', () => this.selectPodcast(p.id));
      list.appendChild(item);
    });
  },

  selectPodcast: async function (podcastId) {
    try {
      const resp = await fetch(`/api/podcasts/${podcastId}`);
      if (!resp.ok) throw new Error('Fehler beim Laden des Podcasts.');
      this.state.activePodcast = await resp.json();
      this.renderActivePodcast();
      this.renderEpisodesTable();
      this.renderArchiveList();
      this.resetAILab();
    } catch (err) {
      this.showToast(err.message, 'danger');
    }
  },

  deletePodcast: async function (podcastId) {
    try {
      const resp = await fetch(`/api/podcasts/${podcastId}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('Löschen fehlgeschlagen.');
      this.showToast('Kanal erfolgreich gelöscht.', 'info');
      this.state.activePodcast = null;
      document.getElementById('activePodcastCard')?.classList.add('d-none');
      await this.fetchArchive();
      this.renderEpisodesTable();
    } catch (err) {
      this.showToast(err.message, 'danger');
    }
  },

  renderActivePodcast: function () {
    const card = document.getElementById('activePodcastCard');
    const p = this.state.activePodcast;
    if (!card || !p) return;

    card.classList.remove('d-none');

    const titleEl = document.getElementById('activePodcastTitle');
    const authorEl = document.getElementById('activePodcastAuthor');
    const epCountEl = document.getElementById('activePodcastEpCount');
    const descEl = document.getElementById('activePodcastDescription');
    const imgEl = document.getElementById('activePodcastImage');
    const badgeEl = document.getElementById('activePodcastPlatformBadge');

    if (titleEl) titleEl.textContent = p.title;
    if (authorEl) authorEl.textContent = p.author || 'Unbekannt';
    if (epCountEl) epCountEl.textContent = `${p.episodes.length} Folgen`;
    if (descEl) descEl.textContent = p.description || 'Keine Beschreibung verfügbar.';
    if (imgEl && p.image_url) imgEl.src = p.image_url;

    if (badgeEl) {
      if (p.platform === 'youtube') {
        badgeEl.className = 'badge badge-youtube';
        badgeEl.textContent = 'YouTube';
      } else if (p.platform === 'apple') {
        badgeEl.className = 'badge badge-apple';
        badgeEl.textContent = 'Apple Podcasts';
      } else {
        badgeEl.className = 'badge badge-rss';
        badgeEl.textContent = 'RSS Feed';
      }
    }
  },

  // ===========================================================================
  // Episodes Table
  // ===========================================================================
  renderEpisodesTable: function () {
    const tbody = document.getElementById('episodesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!this.state.activePodcast || !this.state.activePodcast.episodes) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center text-muted p-4">
            Kein Medienkanal ausgewählt. Wähle einen Podcast im Archiv.
          </td>
        </tr>
      `;
      return;
    }

    const eps = this.state.activePodcast.episodes.filter(e => {
      if (!this.state.filterQuery) return true;
      return (e.title || '').toLowerCase().includes(this.state.filterQuery);
    });

    if (eps.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center text-muted p-4">
            Keine Episoden für Filter "${this.escapeHtml(this.state.filterQuery)}" gefunden.
          </td>
        </tr>
      `;
      return;
    }

    eps.forEach((ep, index) => {
      const tr = document.createElement('tr');

      const dateStr = ep.published_at ? new Date(ep.published_at).toLocaleDateString('de-DE') : '-';
      const durMinutes = ep.duration_seconds ? `${Math.floor(ep.duration_seconds / 60)} min` : '-';

      let badgesHtml = '';
      if (ep.has_chapters) {
        badgesHtml += '<span class="badge bg-secondary me-1" title="Kapitel vorhanden">⏱️ Kapitel</span>';
      }
      if (ep.has_transcript) {
        badgesHtml += '<span class="badge bg-success" title="Transkript verfügbar">📜 Transkript</span>';
      } else {
        badgesHtml += '<span class="badge bg-dark border border-secondary text-muted">Kein Transkript</span>';
      }

      tr.innerHTML = `
        <td class="text-muted small">${ep.episode_number || (index + 1)}</td>
        <td>
          <div class="fw-semibold text-truncate" style="max-width: 320px;" title="${this.escapeHtml(ep.title)}">
            ${this.escapeHtml(ep.title)}
          </div>
        </td>
        <td class="small text-muted">${dateStr}</td>
        <td class="small text-muted">${durMinutes}</td>
        <td>${badgesHtml}</td>
        <td style="text-align: right;">
          <button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="app.openDrawer('${ep.id}')">
            Details 🔍
          </button>
        </td>
      `;

      tbody.appendChild(tr);
    });
  },

  // ===========================================================================
  // Episode Drawer (Offcanvas)
  // ===========================================================================
  openDrawer: async function (episodeId) {
    try {
      const resp = await fetch(`/api/episodes/${episodeId}`);
      if (!resp.ok) throw new Error('Fehler beim Laden der Episoden-Details.');
      const ep = await resp.json();
      this.state.activeEpisode = ep;

      // Drawer Header
      document.getElementById('drawerEpisodeTitle').textContent = ep.title;
      const dateStr = ep.published_at ? new Date(ep.published_at).toLocaleDateString('de-DE') : 'Unbekannt';
      const durStr = ep.duration_seconds ? `${Math.floor(ep.duration_seconds / 60)} Minuten` : 'Dauer unbekannt';
      document.getElementById('drawerEpisodeSub').textContent = `Folge #${ep.episode_number || '-'} • ${dateStr} • ${durStr}`;

      // Badges
      const badgesContainer = document.getElementById('drawerBadges');
      badgesContainer.innerHTML = '';
      if (ep.audio_or_video_url) {
        const link = document.createElement('a');
        link.href = ep.audio_or_video_url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.className = 'btn btn-outline-info btn-sm py-0 px-2';
        link.textContent = '🔗 Original-Medienlink öffnen';
        badgesContainer.appendChild(link);
      }

      // Show Notes
      document.getElementById('drawerNotesContent').textContent = ep.description || 'Keine Show Notes hinterlegt.';

      // Chapters
      const chaptersContainer = document.getElementById('drawerChaptersList');
      chaptersContainer.innerHTML = '';
      if (ep.chapters && ep.chapters.length > 0) {
        ep.chapters.forEach(ch => {
          const div = document.createElement('div');
          div.className = 'd-flex justify-content-between p-1 border-bottom border-secondary small';
          div.innerHTML = `
            <span>${this.escapeHtml(ch.title)}</span>
            <span class="badge bg-secondary">${ch.start_time_formatted || ch.start_time}s</span>
          `;
          chaptersContainer.appendChild(div);
        });
      } else {
        chaptersContainer.innerHTML = '<div class="text-muted small">Keine Kapitelmarken für diese Folge vorhanden.</div>';
      }

      // Transcript
      this.renderDrawerTranscript(ep);

      // Show Drawer
      document.getElementById('episodeDrawer')?.classList.add('show');
      const backdrop = document.getElementById('drawerBackdrop');
      if (backdrop) backdrop.style.display = 'block';
    } catch (err) {
      this.showToast(err.message, 'danger');
    }
  },

  renderDrawerTranscript: function (ep) {
    const statusEl = document.getElementById('drawerTranscriptStatus');
    const segsEl = document.getElementById('drawerTranscriptSegments');
    const btn = document.getElementById('drawerFetchTranscriptBtn');

    if (!segsEl) return;
    segsEl.innerHTML = '';

    if (ep.transcript && ep.transcript.full_text) {
      if (statusEl) statusEl.textContent = `Sprache: ${ep.transcript.language || 'de'} (${ep.transcript.segments?.length || 0} Abschnitte)`;
      if (btn) btn.style.display = 'none';

      if (ep.transcript.segments && ep.transcript.segments.length > 0) {
        ep.transcript.segments.forEach(seg => {
          const div = document.createElement('div');
          div.className = 'transcript-segment';
          const mins = Math.floor(seg.start / 60);
          const secs = Math.floor(seg.start % 60);
          const timeStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

          div.innerHTML = `
            <span class="badge bg-dark border border-secondary text-info me-2">${timeStr}</span>
            <span>${this.escapeHtml(seg.text)}</span>
          `;
          segsEl.appendChild(div);
        });
      } else {
        const p = document.createElement('p');
        p.className = 'small text-muted';
        p.textContent = ep.transcript.full_text;
        segsEl.appendChild(p);
      }
    } else {
      if (statusEl) statusEl.textContent = 'Kein Transkript vorhanden';
      if (btn) btn.style.display = 'inline-block';
      segsEl.innerHTML = '<div class="text-muted small">Klicke oben auf "Transkript laden", um den Text abzurufen.</div>';
    }
  },

  fetchEpisodeTranscript: async function (episodeId) {
    const btn = document.getElementById('drawerFetchTranscriptBtn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Lädt...';
    }

    try {
      const resp = await fetch(`/api/episodes/${episodeId}/transcript`, { method: 'POST' });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Transkript konnte nicht geladen werden.');
      }
      const trans = await resp.json();
      this.state.activeEpisode.transcript = trans;
      this.renderDrawerTranscript(this.state.activeEpisode);
      this.showToast('Transkript erfolgreich geladen!', 'success');
      // Update Tabelle
      if (this.state.activePodcast) {
        await this.selectPodcast(this.state.activePodcast.id);
      }
    } catch (err) {
      this.showToast(err.message, 'warning');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Transkript laden';
      }
    }
  },

  closeDrawer: function () {
    document.getElementById('episodeDrawer')?.classList.remove('show');
    const backdrop = document.getElementById('drawerBackdrop');
    if (backdrop) backdrop.style.display = 'none';
  },

  // ===========================================================================
  // Gemini AI Lab
  // ===========================================================================
  resetAILab: function () {
    const wikitext = document.getElementById('wikitextOutput');
    const summary = document.getElementById('summaryOutput');
    const guests = document.getElementById('guestsOutput');
    const qa = document.getElementById('qaOutput');
    const chat = document.getElementById('chatOutput');

    if (wikitext) { wikitext.classList.remove('output-rendered'); wikitext.textContent = 'Klicke auf "Generieren", um die Wikipedia-Tabelle via Gemini AI zu erstellen...'; }
    if (summary)  { summary.classList.remove('output-rendered');  summary.textContent = 'Klicke auf "Analysieren", um eine Executive Summary via Gemini AI zu erstellen...'; }
    if (guests)   { guests.classList.remove('output-rendered');   guests.textContent = 'Klicke auf "Extrahieren", um Gäste und Themenschwerpunkte zu analysieren...'; }
    if (qa)       { qa.classList.remove('output-rendered');       qa.textContent = 'Stelle eine Frage zu den Show Notes oder Transkripten der Episoden...'; }
    if (chat)     { chat.classList.remove('output-rendered');     chat.textContent = 'Schreibe einen beliebigen Analyseauftrag...'; }
  },

  generateWikitext: function () {
    const formatSelect = document.getElementById('wikiFormatSelect');
    const deltaCheck = document.getElementById('wikiDeltaCheck');
    const styleFormat = formatSelect?.value || 'wikitable';
    const onlyNew = !!deltaCheck?.checked;
    this.runAIAnalysis('wikitext_table', null, styleFormat, onlyNew);
  },

  copyWikitext: function () {
    this.copyToClipboard('wikitextOutput');
  },

  searchTranscripts: async function () {
    const input = document.getElementById('transcriptSearchInput');
    const resultsContainer = document.getElementById('transcriptSearchResults');
    const q = input?.value.trim();
    if (!q || !resultsContainer) return;

    resultsContainer.innerHTML = '<div class="text-center p-3 text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Durchsuche Transkripte...</div>';

    try {
      const podId = this.state.activePodcast ? `&podcast_id=${this.state.activePodcast.id}` : '';
      const resp = await fetch(`/api/search/transcripts?q=${encodeURIComponent(q)}${podId}`);
      if (!resp.ok) throw new Error('Suche fehlgeschlagen.');
      const data = await resp.json();

      if (!data.results || data.results.length === 0) {
        resultsContainer.innerHTML = `<div class="text-muted small p-2">Keine Treffer für "${this.escapeHtml(q)}" gefunden.</div>`;
        return;
      }

      resultsContainer.innerHTML = '';
      const countHeader = document.createElement('div');
      countHeader.className = 'small text-info fw-bold mb-2';
      countHeader.textContent = `${data.total_matches} Treffer gefunden:`;
      resultsContainer.appendChild(countHeader);

      data.results.forEach(res => {
        const item = document.createElement('div');
        item.className = 'search-result-item';

        const epNumStr = res.episode_number ? `#${res.episode_number} ` : '';
        const linkHtml = res.deep_link_url
          ? `<a href="${res.deep_link_url}" target="_blank" rel="noopener" class="timestamp-chip">▶️ [${res.timestamp_formatted}]</a>`
          : `<span class="timestamp-chip">[${res.timestamp_formatted}]</span>`;

        const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        const highlightedSnippet = this.escapeHtml(res.matched_text).replace(regex, '<span class="search-highlight">$1</span>');

        item.innerHTML = `
          <div class="d-flex justify-content-between align-items-start mb-1">
            <span class="small fw-bold text-truncate" style="max-width: 220px;" title="${this.escapeHtml(res.episode_title)}">${epNumStr}${this.escapeHtml(res.episode_title)}</span>
            ${linkHtml}
          </div>
          <div class="small text-muted" style="line-height: 1.4;">${highlightedSnippet}</div>
        `;
        resultsContainer.appendChild(item);
      });
    } catch (err) {
      resultsContainer.innerHTML = `<div class="text-danger small p-2">Fehler bei der Suche: ${this.escapeHtml(err.message)}</div>`;
    }
  },

  runAIAnalysis: async function (analysisType, customQuery = null, styleFormat = null, onlyNew = false) {
    if (!this.state.activePodcast) {
      this.showToast('Bitte wähle zuerst einen Podcast aus dem Archiv.', 'warning');
      return;
    }

    let outputEl = null;
    let buttonEl = null;
    const isRawOutput = (analysisType === 'wikitext_table' || analysisType === 'wikipedia_template');

    if (analysisType === 'wikitext_table' || analysisType === 'wikipedia_template') {
      outputEl = document.getElementById('wikitextOutput');
      buttonEl = document.getElementById('genWikitextBtn');
    } else if (analysisType === 'summary') {
      outputEl = document.getElementById('summaryOutput');
      buttonEl = document.getElementById('genSummaryBtn');
    } else if (analysisType === 'guests_topics') {
      outputEl = document.getElementById('guestsOutput');
      buttonEl = document.getElementById('genGuestsBtn');
    } else if (analysisType === 'qa') {
      outputEl = document.getElementById('qaOutput');
      buttonEl = document.getElementById('qaSubmitBtn');
    } else if (analysisType === 'custom_chat') {
      outputEl = document.getElementById('chatOutput');
      buttonEl = document.getElementById('chatSubmitBtn');
    }

    if (outputEl) {
      outputEl.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Gemini analysiert die Medieninhalte...';
      outputEl.classList.remove('output-rendered');
    }
    if (buttonEl) buttonEl.disabled = true;

    try {
      const resp = await fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          podcast_id: this.state.activePodcast.id,
          analysis_type: analysisType,
          custom_query: customQuery,
          style_format: styleFormat,
          only_new_episodes: onlyNew
        })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'KI-Analyse fehlgeschlagen.');
      }

      if (outputEl) {
        if (isRawOutput) {
          outputEl.classList.remove('output-rendered');
          outputEl.textContent = data.response_text;
        } else {
          outputEl.classList.add('output-rendered');
          outputEl.innerHTML = this.renderMarkdown(data.response_text);
        }
      }
    } catch (err) {
      if (outputEl) {
        outputEl.classList.remove('output-rendered');
        outputEl.textContent = `❌ Fehler: ${err.message}`;
      }
      this.showToast(err.message, 'danger');
    } finally {
      if (buttonEl) buttonEl.disabled = false;
    }
  },


  copyToClipboard: function (elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.textContent;
    if (!text || text.startsWith('Klicke auf') || text.startsWith('❌')) {
      this.showToast('Kein Inhalt zum Kopieren vorhanden.', 'warning');
      return;
    }

    navigator.clipboard.writeText(text).then(() => {
      this.showToast('In die Zwischenablage kopiert! 📋', 'success');
    }).catch(() => {
      this.showToast('Kopieren fehlgeschlagen.', 'danger');
    });
  },

  // ===========================================================================
  // Markdown Renderer (CSP-konform, kein externer CDN)
  // ===========================================================================
  /**
   * Wandelt einen Gemini-Markdown-Response in sicheres HTML um.
   * Schritt 1: HTML-Sonderzeichen escapen (XSS-Schutz)
   * Schritt 2: Markdown-Syntax durch HTML-Tags ersetzen
   */
  renderMarkdown: function (text) {
    if (!text) return '';

    // 1. HTML-Sonderzeichen escapen (verhindert XSS durch Modellantwort)
    let html = this.escapeHtml(text);

    // 2. Code-Blöcke zuerst schützen (```...```)
    html = html.replace(/```[\w]*\n?([\s\S]*?)```/g, (match, code) => {
      return `<pre class="bg-dark border border-secondary rounded p-2 mt-2 mb-2 small overflow-auto"><code>${code.trim()}</code></pre>`;
    });

    // 3. Inline-Code (`code`)
    html = html.replace(/`([^`]+?)`/g, '<code class="text-info bg-dark px-1 rounded">$1</code>');

    // 4. Überschriften (### h3, ## h2, # h1)
    html = html.replace(/^###\s+(.+)$/gm, '<p class="fw-bold text-info mb-1 mt-2 small text-uppercase letter-spacing-1">▸ $1</p>');
    html = html.replace(/^##\s+(.+)$/gm, '<h6 class="text-info mt-3 mb-1 border-bottom border-secondary pb-1">$1</h6>');
    html = html.replace(/^#\s+(.+)$/gm, '<h5 class="text-info mt-3 mb-2">$1</h5>');

    // 5. Fett + Kursiv (***text***), Fett (**text**), Kursiv (*text*)
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

    // 6. Horizontale Trennlinie (---)
    html = html.replace(/^---$/gm, '<hr class="border-secondary my-2">');

    // 7. Listen-Elemente (- item oder * item)
    html = html.replace(/^[-*]\s+(.+)$/gm, '<li class="mb-1">$1</li>');
    // Listenelemente in <ul> einpacken
    html = html.replace(/(<li[^>]*>.*?<\/li>\n?)+/gs, (match) => {
      return `<ul class="mt-1 mb-2 ps-3">${match}</ul>`;
    });

    // 8. Nummerierte Listen (1. item)
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li class="mb-1">$1</li>');

    // 9. Zeilenumbrüche (außerhalb von Block-Elementen)
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    return html;
  },

  // ===========================================================================
  // Export Center
  // ===========================================================================
  exportData: function (format) {
    if (!this.state.activePodcast) {
      this.showToast('Bitte wähle zuerst einen Podcast aus dem Archiv.', 'warning');
      return;
    }
    const podcastId = this.state.activePodcast.id;
    window.location.href = `/api/export/${podcastId}?format=${format}`;
  },

  // ===========================================================================
  // Webspace Publisher (Geminispace & Gopherspace)
  // ===========================================================================
  publishWebspaces: async function () {
    const btn = document.getElementById('publishWebspacesBtn');
    const spinner = document.getElementById('publishSpinner');
    const statusBadge = document.getElementById('publishStatusBadge');

    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    if (statusBadge) statusBadge.textContent = 'Generiere Dateien in public/gemini und public/gopher...';

    try {
      const resp = await fetch('/api/publish', { method: 'POST' });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || 'Fehler beim Publizieren der Webspaces.');
      }

      const msg = `Erfolgreich publiziert: ${data.gemini_files_count} Gemini-Dateien (.gmi), ${data.gopher_files_count} Gophermaps.`;
      this.showToast(msg, 'success');
      if (statusBadge) {
        statusBadge.textContent = `✅ Publiziert: ${data.podcast_count} Podcasts (${data.gemini_files_count} .gmi / ${data.gopher_files_count} gophermaps)`;
      }
    } catch (err) {
      this.showToast(err.message, 'danger');
      if (statusBadge) statusBadge.textContent = '❌ Fehler beim Publizieren';
    } finally {
      if (btn) btn.disabled = false;
      if (spinner) spinner.classList.add('d-none');
    }
  },

  // ===========================================================================
  // Utilities & Notifications
  // ===========================================================================
  showToast: function (message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `custom-toast border-${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'danger') icon = '❌';

    toast.innerHTML = `<span class="me-2">${icon}</span><span>${this.escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  escapeHtml: function (str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};

// Initialisierung bei DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  app.init();
});
