// =============================================================================
// KIOTVIET CRM ANALYTICS - PHẦN CỨNG TOÀN QUỐC MODULE (pctq.js)
// Doanh thu theo Coacher & Nhân sự Toàn Quốc (Sheet: phancungtoanquoc A1:M40)
// =============================================================================
        // PCTQ MODULE - Phần Cứng Toàn Quốc
        // ==========================================
        const PCTQ_API = `${ENDPOINT_API_URL}?sheet=phancungtoanquoc&range=A1:M40`;
        let rawPCTQData = [];
        let pctqLoaded = false;
        let pctqFilterCoacher = '';
        let pctqActiveMonth = 'all';
        let pctqSortBy = 'grand';
        let pctqChartInst = null;
        let pctqCoachChartInst = null;

        const fmt = (v) => v ? new Intl.NumberFormat('vi-VN').format(Math.round(v)) + ' ₫' : '0 ₫';
        const toNum = (v) => {
            if (typeof v === 'number') return v;
            const s = String(v || '').replace(/[^0-9.]/g, '');
            return parseFloat(s) || 0;
        };

        async function fetchPCTQLive(force = false) {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');
            updateLoadingProgress(25, 'Đang kéo số liệu phancungtoanquoc mới nhất... 25%');

            try {
                const url = `${ENDPOINT_API_URL}?sheet=phancungtoanquoc&range=A1:M40&_t=${Date.now()}`;
                const res = await fetch(url, { cache: 'no-cache' });
                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    rawPCTQData = parsePCTQ(json.data);
                    populatePCTQFilters();
                    renderPCTQDashboard();
                    updateLoadingProgress(100, `Live API: ${rawPCTQData.length} dòng phancungtoanquoc (100% • ${new Date().toLocaleTimeString()})`, false, true);
                } else {
                    updateLoadingProgress(100, 'Không lấy được dữ liệu từ sheet phancungtoanquoc', true, false);
                }
            } catch(e) {
                console.warn('PCTQ fetch error:', e);
                updateLoadingProgress(100, 'Lỗi kết nối API phancungtoanquoc', true, false);
            } finally {
                if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
            }
        }

        function parsePCTQ(rows) {
            const result = [];
            for (let i = 1; i < rows.length; i++) {
                const r = rows[i];
                const name = String(r[2] || '').trim();
                if (!name) continue;
                const level = String(r[4] || '').trim();
                let t7Val = toNum(r[6]);
                let pxk7Val = String(r[7] || '').trim();
                let don7Val = parseInt(String(r[8] || '0')) || 0;
                let t8Val = toNum(r[9]);
                let pxk8Val = String(r[10] || '').trim();
                let t9Val = toNum(r[11]);
                let pxk9Val = String(r[12] || '').trim();

                // Trường hợp đặc biệt: ô Tháng 7 bị nhập nhầm text (ví dụ tên coacher) và số tiền bị đẩy sang cột H
                if (t7Val === 0 && toNum(r[7]) > 0 && typeof r[6] === 'string' && r[6].length > 3) {
                    t7Val = toNum(r[7]);
                    pxk7Val = String(r[8] || '').trim();
                    don7Val = 0;
                }

                result.push({
                    stt:      r[0],
                    ma:       r[1],
                    name:     name,
                    kvuc:     String(r[3] || '').trim(),
                    level:    level,
                    coacher:  String(r[5] || '').trim(),
                    t7:       t7Val,
                    pxk7:     pxk7Val,
                    don7:     don7Val,
                    t8:       t8Val,
                    pxk8:     pxk8Val,
                    t9:       t9Val,
                    pxk9:     pxk9Val,
                    isCoacher: level === 'Coacher'
                });
            }
            return result;
        }

        function getPCTQFiltered() {
            return rawPCTQData.filter(r => {
                // Coacher row: coacher field = chính tên họ → vẫn match filter
                if (pctqFilterCoacher) {
                    // Với row coacher: r.coacher = tên coacher = r.name → match đúng
                    if (r.coacher !== pctqFilterCoacher) return false;
                }
                return true;
            });
        }

        function setPCTQMonth(m) {
            pctqActiveMonth = m;
            ['all','7','8','9'].forEach(x => {
                const btn = document.getElementById('pctqPill' + (x === 'all' ? 'All' : x));
                if (btn) btn.className = (m === x)
                    ? 'px-2.5 py-1 rounded-lg text-xs font-semibold bg-violet-600 text-white transition'
                    : 'px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';
            });
            renderPCTQDashboard();
        }

        function setPCTQSort(key) {
            pctqSortBy = key;
            ['grand','t7','t8','t9'].forEach(k => {
                const btn = document.getElementById('pctqSort' + k.charAt(0).toUpperCase() + k.slice(1));
                if (btn) btn.className = (k === key)
                    ? 'px-2.5 py-1 rounded-lg text-xs font-semibold bg-violet-600 text-white transition'
                    : 'px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';
            });
            renderPCTQDashboard();
        }

        function applyPCTQFilters() {
            pctqFilterCoacher = document.getElementById('pctqFilterCoacher')?.value || '';
            renderPCTQDashboard();
        }

        function resetPCTQFilters() {
            pctqFilterCoacher = '';
            pctqActiveMonth = 'all';
            pctqSortBy = 'grand';
            const sel = document.getElementById('pctqFilterCoacher');
            if (sel) sel.value = '';
            setPCTQMonth('all');
            setPCTQSort('grand');
        }

        function populatePCTQFilters() {
            const coaches = [...new Set(rawPCTQData.map(r => r.coacher).filter(Boolean))].sort();
            const sel = document.getElementById('pctqFilterCoacher');
            if (!sel) return;
            sel.innerHTML = '<option value="">Tất cả Coacher</option>';
            coaches.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                sel.appendChild(opt);
            });
        }

        function renderPCTQDashboard() {
            const rows = getPCTQFiltered();
            const sorted = [...rows].sort((a, b) => {
                const keyMap = { grand: a.t7+a.t8+a.t9, t7: a.t7, t8: a.t8, t9: a.t9 };
                const keyMapB = { grand: b.t7+b.t8+b.t9, t7: b.t7, t8: b.t8, t9: b.t9 };
                return (keyMapB[pctqSortBy] || 0) - (keyMap[pctqSortBy] || 0);
            });

            const t7Total = rows.reduce((s,r) => s + r.t7, 0);
            const t8Total = rows.reduce((s,r) => s + r.t8, 0);
            const t9Total = rows.reduce((s,r) => s + r.t9, 0);
            const grand = t7Total + t8Total + t9Total;

            // KPI cards
            const el = (id) => document.getElementById(id);
            if (el('pctqKpiT7')) el('pctqKpiT7').textContent = fmt(t7Total);
            if (el('pctqKpiT8')) el('pctqKpiT8').textContent = fmt(t8Total);
            if (el('pctqKpiT9')) el('pctqKpiT9').textContent = fmt(t9Total);
            if (el('pctqKpiGrand')) el('pctqKpiGrand').textContent = fmt(grand);
            if (el('pctqKpiT7Sub')) el('pctqKpiT7Sub').textContent = rows.filter(r=>r.t7>0).length + ' SC có doanh thu';
            if (el('pctqKpiT8Sub')) el('pctqKpiT8Sub').textContent = rows.filter(r=>r.t8>0).length + ' SC có doanh thu';
            if (el('pctqKpiT9Sub')) el('pctqKpiT9Sub').textContent = rows.filter(r=>r.t9>0).length + ' SC có doanh thu';
            if (el('pctqKpiGrandSub')) el('pctqKpiGrandSub').textContent = rows.length + ' SC trong bộ lọc';

            // Banner
            if (el('pctqBannerT7')) el('pctqBannerT7').textContent = fmt(t7Total);
            if (el('pctqBannerT8')) el('pctqBannerT8').textContent = fmt(t8Total);
            if (el('pctqBannerT9')) el('pctqBannerT9').textContent = fmt(t9Total);
            if (el('pctqSummaryText')) el('pctqSummaryText').textContent =
                `Đang hiển thị ${rows.length} SC${pctqFilterCoacher ? ' (Coacher: ' + pctqFilterCoacher + ')' : ''} | Tổng 3 tháng: ${fmt(grand)}`;
            if (el('pctqTableCount')) el('pctqTableCount').textContent = rows.length;

            // Grouped bar chart (so sánh 3 tháng theo SC)
            // Show only up to 15 rows in chart for readability
            const chartRows = sorted.slice(0, 15);
            const shortName = (n) => {
                const parts = n.split(' - ');
                return parts.length >= 2 ? parts[0].trim() + ' ' + parts[1].trim().split(' ').slice(-1)[0] : n;
            };
            const labels = chartRows.map(r => shortName(r.name));
            const d7 = chartRows.map(r => r.t7 / 1e6);
            const d8 = chartRows.map(r => r.t8 / 1e6);
            const d9 = chartRows.map(r => r.t9 / 1e6);

            const scCtx = el('pctqSCChart');
            if (scCtx) {
                if (pctqChartInst) pctqChartInst.destroy();
                // Determine datasets based on active month filter
                let datasets;
                if (pctqActiveMonth === 'all') {
                    datasets = [
                        { label: 'Tháng 7', data: d7, backgroundColor: 'rgba(56,189,248,0.75)', borderColor: '#38bdf8', borderWidth: 1, borderRadius: 4 },
                        { label: 'Tháng 8', data: d8, backgroundColor: 'rgba(52,211,153,0.75)', borderColor: '#34d399', borderWidth: 1, borderRadius: 4 },
                        { label: 'Tháng 9', data: d9, backgroundColor: 'rgba(251,191,36,0.75)', borderColor: '#fbbf24', borderWidth: 1, borderRadius: 4 }
                    ];
                } else {
                    const mMap = { '7': { data: d7, color: 'rgba(56,189,248,0.8)', border: '#38bdf8', label: 'Tháng 7' },
                                   '8': { data: d8, color: 'rgba(52,211,153,0.8)', border: '#34d399', label: 'Tháng 8' },
                                   '9': { data: d9, color: 'rgba(251,191,36,0.8)', border: '#fbbf24', label: 'Tháng 9' } };
                    const m = mMap[pctqActiveMonth];
                    datasets = [{ label: m.label, data: m.data, backgroundColor: m.color, borderColor: m.border, borderWidth: 1, borderRadius: 4 }];
                }
                pctqChartInst = new Chart(scCtx, {
                    type: 'bar',
                    data: { labels, datasets },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: true, labels: { color: '#94a3b8', font: { size: 11 } } },
                                   tooltip: { callbacks: { label: ctx => ' ' + ctx.dataset.label + ': ' + new Intl.NumberFormat('vi-VN').format(Math.round(ctx.raw * 1e6)) + ' ₫' } } },
                        scales: {
                            x: { ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 40, minRotation: 20 }, grid: { color: 'rgba(255,255,255,0.03)' } },
                            y: { ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => v + 'M' }, grid: { color: 'rgba(255,255,255,0.06)' } }
                        }
                    }
                });
            }

            // Coach donut chart
            const coachMap = {};
            rows.forEach(r => {
                if (!r.coacher) return;
                if (!coachMap[r.coacher]) coachMap[r.coacher] = { t7: 0, t8: 0, t9: 0 };
                coachMap[r.coacher].t7 += r.t7;
                coachMap[r.coacher].t8 += r.t8;
                coachMap[r.coacher].t9 += r.t9;
            });
            const coachNames = Object.keys(coachMap);
            const coachTotals = coachNames.map(c => coachMap[c].t7 + coachMap[c].t8 + coachMap[c].t9);
            const coachColors = ['#8b5cf6','#06b6d4','#f59e0b','#10b981','#f43f5e'];

            const coachCtx = el('pctqCoachChart');
            if (coachCtx) {
                if (pctqCoachChartInst) pctqCoachChartInst.destroy();
                pctqCoachChartInst = new Chart(coachCtx, {
                    type: 'doughnut',
                    data: {
                        labels: coachNames,
                        datasets: [{ data: coachTotals.map(v => v / 1e6), backgroundColor: coachColors, borderColor: '#0f172a', borderWidth: 2 }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: { label: ctx => ' ' + ctx.label + ': ' + new Intl.NumberFormat('vi-VN').format(Math.round(ctx.raw * 1e6)) + ' ₫' } }
                        }
                    }
                });
                const legend = el('pctqCoachLegend');
                if (legend) {
                    legend.innerHTML = coachNames.map((c, i) => {
                        const total = coachTotals[i];
                        const pct = grand > 0 ? (total / grand * 100).toFixed(1) : 0;
                        const t = coachMap[c];
                        return `<div class="flex flex-col gap-0.5 py-1.5 border-b border-slate-800/60 last:border-0">
                            <div class="flex items-center justify-between gap-2">
                                <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full" style="background:${coachColors[i]}"></span><strong>${c}</strong></span>
                                <span class="text-violet-300 font-bold">${pct}%</span>
                            </div>
                            <div class="flex gap-3 text-[10px] text-slate-500 pl-4">
                                <span class="text-sky-400">T7: ${fmt(t.t7)}</span>
                                <span class="text-emerald-400">T8: ${fmt(t.t8)}</span>
                                <span class="text-amber-400">T9: ${fmt(t.t9)}</span>
                            </div>
                        </div>`;
                    }).join('');
                }
            }

            // Table
            const tbody = el('pctqTableBody');
            const tfoot = el('pctqTableFoot');
            if (!tbody) return;

            const trendIcon = (t7, t8, t9) => {
                const last = pctqActiveMonth === '7' ? t7 : pctqActiveMonth === '8' ? t8 : pctqActiveMonth === '9' ? t9 : t9;
                const prev = pctqActiveMonth === '9' ? t8 : pctqActiveMonth === '8' ? t7 : t8;
                const a = [t7, t8, t9].filter(v => v > 0);
                if (a.length < 2) return '<span class="text-slate-600">—</span>';
                const trending = last > prev ? 1 : last < prev ? -1 : 0;
                if (t9 >= t8 && t8 >= t7 && t7 > 0) return '<span class="text-emerald-400">▲▲ Tăng đều</span>';
                if (t9 <= t8 && t8 <= t7 && t7 > 0) return '<span class="text-rose-400">▼▼ Giảm đều</span>';
                if (trending > 0) return '<span class="text-emerald-400">↑ Tăng</span>';
                if (trending < 0) return '<span class="text-rose-400">↓ Giảm</span>';
                return '<span class="text-slate-400">→ Ổn định</span>';
            };

            const levelBadge = (l) => {
                const m = { 
                    'Level 1': 'bg-sky-500/20 text-sky-300', 
                    'Level 2': 'bg-emerald-500/20 text-emerald-300', 
                    'Level 3': 'bg-amber-500/20 text-amber-300',
                    'Coacher': 'bg-violet-500/30 text-violet-300 font-bold border border-violet-500/50'
                };
                return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${m[l] || 'bg-slate-700 text-slate-300'}">${l}</span>`;
            };

            const highlightMonth = (v, m) => {
                if (pctqActiveMonth === m) return `<strong class="text-yellow-300">${fmt(v)}</strong>`;
                return v > 0 ? fmt(v) : '<span class="text-slate-600">—</span>';
            };

            tbody.innerHTML = sorted.map((r, idx) => {
                const g = r.t7 + r.t8 + r.t9;
                return `<tr class="hover:bg-slate-800/40 transition text-slate-300">
                    <td class="py-2.5 px-3 text-center text-slate-500">${idx + 1}</td>
                    <td class="py-2.5 px-4">
                        <span class="font-semibold text-white">${r.name}</span>
                        ${r.kvuc ? `<span class="ml-1 text-[10px] text-slate-500">(${r.kvuc})</span>` : ''}
                    </td>
                    <td class="py-2.5 px-3 text-center text-slate-400">${r.kvuc || '—'}</td>
                    <td class="py-2.5 px-3 text-center">${levelBadge(r.level)}</td>
                    <td class="py-2.5 px-3 text-center text-indigo-300 font-medium">${r.coacher || '—'}</td>
                    <td class="py-2.5 px-4 text-right text-sky-300">${highlightMonth(r.t7, '7')}</td>
                    <td class="py-2.5 px-4 text-right text-emerald-300">${highlightMonth(r.t8, '8')}</td>
                    <td class="py-2.5 px-4 text-right text-amber-300">${highlightMonth(r.t9, '9')}</td>
                    <td class="py-2.5 px-4 text-right text-violet-300 font-bold">${fmt(g)}</td>
                    <td class="py-2.5 px-3 text-center">${trendIcon(r.t7, r.t8, r.t9)}</td>
                </tr>`;
            }).join('');

            if (tfoot) tfoot.innerHTML = `<tr>
                <td class="py-3 px-3 text-center" colspan="5">TỔNG</td>
                <td class="py-3 px-4 text-right text-sky-300">${fmt(t7Total)}</td>
                <td class="py-3 px-4 text-right text-emerald-300">${fmt(t8Total)}</td>
                <td class="py-3 px-4 text-right text-amber-300">${fmt(t9Total)}</td>
                <td class="py-3 px-4 text-right text-violet-300">${fmt(grand)}</td>
                <td></td>
            </tr>`;
        }

