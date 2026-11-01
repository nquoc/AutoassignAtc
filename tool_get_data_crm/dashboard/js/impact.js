// =============================================================================
// KIOTVIET CRM ANALYTICS - CS IMPACT MODULE (impact.js)
// Phân tích tỷ lệ Impact & Hiệu suất theo Nhân sự & Tỉnh thành (Tab: tudaunam)
// =============================================================================
        const MONTH_COLORS = {
            '5': { border: '#94a3b8', bg: 'rgba(148, 163, 184, 0.85)', solid: '#94a3b8' }, 
            '6': { border: '#38bdf8', bg: 'rgba(56, 189, 248, 0.85)', solid: '#38bdf8' },  
            '7': { border: '#818cf8', bg: 'rgba(129, 140, 248, 0.85)', solid: '#818cf8' }, 
            '8': { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.85)', solid: '#f59e0b' },  
            '9': { border: '#10b981', bg: 'rgba(16, 185, 129, 0.85)', solid: '#10b981' }   
        };
        const PALETTE_FALLBACK = ['#a855f7', '#ec4899', '#f43f5e', '#06b6d4', '#84cc16'];

        // ENDPOINT_API_URL được chia sẻ từ app.js

        // Biến toàn cục quản lý trạng thái
        let rawRecords = [];            
        let currentData = INITIAL_DATA;
        let availableMonths = ['5', '6', '7', '8', '9']; 
        let selectedMonths = new Set(['5', '6', '7', '8', '9']); 
        let currentViewMode = 'impact'; 
        let currentSortMode = 'rate';   
        let currentChartType = 'bar';   
        let chartInstance = null;

        // Cập nhật thanh tiến trình tải dữ liệu & % hiển thị
        // Tách tên ngắn gọn cho đẹp mắt
        function parseShortName(fullName) {
            const parts = (fullName || '').split(' - ');
            if (parts.length >= 2) {
                return parts[1];
            }
            return fullName;
        }

        // Định màu & đánh giá dựa trên tỷ lệ Impact %
        function getImpactColor(rate) {
            if (rate >= 75) return { bg: '#10b981', text: 'text-emerald-400', badge: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', label: 'Xuất sắc' };
            if (rate >= 60) return { bg: '#3b82f6', text: 'text-blue-400', badge: 'bg-blue-500/10 text-blue-400 border border-blue-500/20', label: 'Tốt' };
            if (rate >= 40) return { bg: '#f59e0b', text: 'text-amber-400', badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', label: 'Đạt' };
            return { bg: '#f43f5e', text: 'text-rose-400', badge: 'bg-rose-500/10 text-rose-400 border border-rose-500/20', label: 'Cần cải thiện' };
        }

        // Lấy màu cho tháng
        function getMonthColor(m, idx) {
            if (MONTH_COLORS[m]) return MONTH_COLORS[m];
            const fallback = PALETTE_FALLBACK[idx % PALETTE_FALLBACK.length];
            return { border: fallback, bg: fallback, solid: fallback };
        }

        // Render các nút Pills chọn tháng (Multi-select)
        function renderMonthPills() {
            const container = document.getElementById('monthPillContainer');
            if (!container) return;
            container.innerHTML = '';

            const isAllSelected = availableMonths.length > 0 && availableMonths.every(m => selectedMonths.has(m));

            // Nút "Tất cả"
            const allBtn = document.createElement('button');
            allBtn.type = 'button';
            allBtn.className = isAllSelected
                ? 'px-2.5 py-1 rounded-lg text-xs font-bold bg-blue-600 text-white shadow-sm shadow-blue-500/30 transition'
                : 'px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700 transition';
            allBtn.innerText = 'Tất cả';
            allBtn.onclick = () => toggleAllMonths();
            container.appendChild(allBtn);

            // Các nút từng Tháng: T5, T6, T7, T8, T9...
            availableMonths.forEach((m, idx) => {
                const isSelected = selectedMonths.has(m);
                const btn = document.createElement('button');
                btn.type = 'button';
                const col = getMonthColor(m, idx).solid;
                
                if (isSelected) {
                    btn.className = 'px-2.5 py-1 rounded-lg text-xs font-bold text-white transition flex items-center gap-1 shadow-sm';
                    btn.style.backgroundColor = col;
                } else {
                    btn.className = 'px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700 transition flex items-center gap-1 opacity-60';
                }
                btn.innerHTML = `<span>T${m}</span>`;
                btn.onclick = () => toggleMonth(m);
                container.appendChild(btn);
            });
        }

        // Toggle chọn/bỏ chọn từng tháng
        function toggleMonth(m) {
            if (selectedMonths.has(m)) {
                if (selectedMonths.size > 1) {
                    selectedMonths.delete(m);
                } else {
                    return;
                }
            } else {
                selectedMonths.add(m);
            }
            renderMonthPills();
            applyFilters();
        }

        // Toggle Tất cả tháng
        function toggleAllMonths() {
            const isAllSelected = availableMonths.every(m => selectedMonths.has(m));
            if (isAllSelected) {
                const latest = availableMonths[availableMonths.length - 1];
                selectedMonths.clear();
                if (latest) selectedMonths.add(latest);
            } else {
                availableMonths.forEach(m => selectedMonths.add(m));
            }
            renderMonthPills();
            applyFilters();
        }

        // Đổ dữ liệu vào các dropdown Ngày, Tỉnh/Thành phố
        function populateFilterDropdowns(records) {
            if (!records || records.length === 0) return;

            const monthSet = new Set();
            const daySet = new Set();
            const citySet = new Set();

            records.forEach(r => {
                if (r.month) monthSet.add(r.month);
                if (r.day) daySet.add(r.day);
                if (r.city) citySet.add(r.city);
            });

            // 1. Cập nhật availableMonths & selectedMonths
            const sortedMonths = Array.from(monthSet).sort((a, b) => {
                const na = parseInt(a), nb = parseInt(b);
                return (isNaN(na) || isNaN(nb)) ? a.localeCompare(b) : na - nb;
            });
            if (sortedMonths.length > 0) {
                availableMonths = sortedMonths;
                if (selectedMonths.size === 0) {
                    availableMonths.forEach(m => selectedMonths.add(m));
                }
            }
            renderMonthPills();

            // 2. Dropdown Ngày
            const daySelect = document.getElementById('filterDay');
            const curDay = daySelect.value;
            daySelect.innerHTML = '<option value="">Tất cả ngày</option>';
            const sortedDays = Array.from(daySet).sort((a, b) => parseInt(a) - parseInt(b));
            sortedDays.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = `Ngày ${d}`;
                if (d === curDay) opt.selected = true;
                daySelect.appendChild(opt);
            });

            // 3. Dropdown Tỉnh/Thành phố
            const citySelect = document.getElementById('filterCity');
            const curCity = citySelect.value;
            citySelect.innerHTML = '<option value="">Tất cả tỉnh thành</option>';
            const sortedCities = Array.from(citySet).sort((a, b) => a.localeCompare(b, 'vi'));
            sortedCities.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                if (c === curCity) opt.selected = true;
                citySelect.appendChild(opt);
            });
        }

        // Áp dụng bộ lọc động và tính toán số liệu real-time
        function applyFilters() {
            const filterDay = document.getElementById('filterDay') ? document.getElementById('filterDay').value : '';
            const filterCity = document.getElementById('filterCity') ? document.getElementById('filterCity').value : '';
            const searchInput = document.getElementById('searchInput');
            const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

            // Nếu chưa có rawRecords (dùng fallback ban đầu)
            if (!rawRecords || rawRecords.length === 0) {
                renderKPIs(currentData);
                renderChart();
                renderTable(currentViewMode === 'city' ? (currentData.city_data || []) : (currentData.staff_data || []));
                return;
            }

            // Lọc dữ liệu theo:
            // 1. Multi-select Tháng (trong selectedMonths)
            // 2. Ngày
            // 3. Tỉnh/TP
            // 4. Tìm kiếm từ khoá
            const filtered = rawRecords.filter(r => {
                if (selectedMonths.size > 0 && !selectedMonths.has(r.month)) return false;
                if (filterDay && r.day !== filterDay) return false;
                if (filterCity && r.city !== filterCity) return false;
                if (query) {
                    if (currentViewMode === 'city') {
                        if (!r.city.toLowerCase().includes(query)) return false;
                    } else {
                        if (!r.staff.toLowerCase().includes(query)) return false;
                    }
                }
                return true;
            });

            // Gom nhóm theo Nhân sự và Tỉnh/Thành phố
            const staffMap = {};
            const cityMap = {};
            let totalRows = filtered.length;
            let totalImpact1 = 0;
            let totalImpact0 = 0;

            filtered.forEach(r => {
                // Gom nhân sự
                const name = r.staff;
                if (!staffMap[name]) {
                    staffMap[name] = { 
                        name: name, 
                        count: 0, 
                        impact1: 0, 
                        impact0: 0, 
                        done: 0,
                        months: {} 
                    };
                }
                const s = staffMap[name];
                s.count++;
                if (r.impact === 1) {
                    s.impact1++;
                    totalImpact1++;
                } else {
                    s.impact0++;
                    totalImpact0++;
                }
                if (r.status && r.status.toLowerCase().includes('đã làm')) {
                    s.done++;
                }

                const m = r.month || 'NA';
                if (!s.months[m]) {
                    s.months[m] = { count: 0, impact1: 0, impact0: 0, rate: 0 };
                }
                s.months[m].count++;
                if (r.impact === 1) s.months[m].impact1++;
                else s.months[m].impact0++;

                // Gom tỉnh/thành phố
                const cName = r.city || 'Chưa xác định';
                if (!cityMap[cName]) {
                    cityMap[cName] = { name: cName, count: 0, impact1: 0, impact0: 0 };
                }
                cityMap[cName].count++;
                if (r.impact === 1) cityMap[cName].impact1++;
                else cityMap[cName].impact0++;
            });

            // Tính tỷ lệ % impact từng tháng cho từng nhân sự
            Object.values(staffMap).forEach(s => {
                Object.keys(s.months).forEach(m => {
                    const mData = s.months[m];
                    mData.rate = mData.count > 0 ? +(mData.impact1 * 100 / mData.count).toFixed(1) : 0;
                });
            });

            const teamImpactRate = totalRows > 0 ? +(totalImpact1 * 100 / totalRows).toFixed(1) : 0;

            // Danh sách tháng đang chọn sắp xếp theo thứ tự thời gian
            const activeSortedMonths = Array.from(selectedMonths).sort((a, b) => {
                const na = parseInt(a), nb = parseInt(b);
                return (isNaN(na) || isNaN(nb)) ? a.localeCompare(b) : na - nb;
            });

            // Chuyển sang mảng danh sách nhân sự
            let staffList = Object.values(staffMap).map(s => {
                const rate = s.count > 0 ? +(s.impact1 * 100 / s.count).toFixed(1) : 0;
                const pct = totalRows > 0 ? +(s.count * 100 / totalRows).toFixed(2) : 0;

                let delta = null;
                if (activeSortedMonths.length >= 2) {
                    const lastM = activeSortedMonths[activeSortedMonths.length - 1];
                    const prevM = activeSortedMonths[activeSortedMonths.length - 2];
                    if (s.months[lastM] && s.months[prevM]) {
                        delta = +(s.months[lastM].rate - s.months[prevM].rate).toFixed(1);
                    }
                }

                return {
                    name: s.name,
                    count: s.count,
                    impact1: s.impact1,
                    impact0: s.impact0,
                    impact_rate: rate,
                    percentage: pct,
                    done: s.done,
                    months: s.months,
                    delta: delta
                };
            });

            // Chuyển sang mảng danh sách Tỉnh/Thành phố
            let cityList = Object.values(cityMap).map(c => {
                const rate = c.count > 0 ? +(c.impact1 * 100 / c.count).toFixed(1) : 0;
                const pct = totalRows > 0 ? +(c.count * 100 / totalRows).toFixed(2) : 0;
                return {
                    name: c.name,
                    count: c.count,
                    impact1: c.impact1,
                    impact0: c.impact0,
                    impact_rate: rate,
                    percentage: pct
                };
            });

            // Sắp xếp theo lựa chọn (% Impact hoặc Số dòng)
            if (currentSortMode === 'rate') {
                staffList.sort((a, b) => b.impact_rate - a.impact_rate || b.count - a.count);
                cityList.sort((a, b) => b.impact_rate - a.impact_rate || b.count - a.count);
            } else {
                staffList.sort((a, b) => b.count - a.count || b.impact_rate - a.impact_rate);
                cityList.sort((a, b) => b.count - a.count || b.impact_rate - a.impact_rate);
            }

            // Gán lại rank
            staffList = staffList.map((s, idx) => ({ ...s, rank: idx + 1 }));
            cityList = cityList.map((c, idx) => ({ ...c, rank: idx + 1 }));

            currentData = {
                tab_name: 'tudaunam',
                total_rows: totalRows,
                total_impact1: totalImpact1,
                total_impact0: totalImpact0,
                team_impact_rate: teamImpactRate,
                total_staff: staffList.length,
                staff_data: staffList,
                city_data: cityList,
                selected_months_list: activeSortedMonths
            };

            // Cập nhật thanh tóm tắt bộ lọc
            const summaryEl = document.getElementById('filterSummaryText');
            if (summaryEl) {
                const parts = [];
                if (activeSortedMonths.length === availableMonths.length && availableMonths.length > 0) {
                    parts.push(`Tất cả ${availableMonths.length} tháng (T${availableMonths.join(', T')})`);
                } else if (activeSortedMonths.length > 0) {
                    parts.push(`Tháng ${activeSortedMonths.join(', ')}`);
                }
                if (filterDay) parts.push(`Ngày ${filterDay}`);
                if (filterCity) parts.push(filterCity);
                if (query) parts.push(`Tìm: "${query}"`);
                
                const filterDesc = parts.length > 0 ? ` (${parts.join(' • ')})` : '';
                summaryEl.innerText = `Hiển thị ${totalRows.toLocaleString('vi-VN')} dòng dữ liệu${filterDesc}`;
            }

            const b1 = document.getElementById('bannerImpact1');
            const b0 = document.getElementById('bannerImpact0');
            const bRate = document.getElementById('bannerImpactRate');
            if (b1) b1.innerText = totalImpact1.toLocaleString('vi-VN');
            if (b0) b0.innerText = totalImpact0.toLocaleString('vi-VN');
            if (bRate) bRate.innerText = `${teamImpactRate}%`;

            // Render lại giao diện
            renderKPIs(currentData);
            renderChart();
            renderTable(currentViewMode === 'city' ? cityList : staffList);
        }

        // Cập nhật các thẻ KPI trên cùng
        function renderKPIs(data) {
            document.getElementById('tabNameText').innerText = data.tab_name || 'tudaunam';
            document.getElementById('kpiTotalRows').innerText = (data.total_rows || 0).toLocaleString('vi-VN');

            const card1Title = document.getElementById('kpiCard1Title');
            const card2Title = document.getElementById('kpiCard2Title');
            const card2Val = document.getElementById('kpiCard2Val');
            const card2Sub = document.getElementById('kpiCard2Sub');
            const card3Title = document.getElementById('kpiCard3Title');
            const card3Val = document.getElementById('kpiCard3Val');
            const card3Sub = document.getElementById('kpiCard3Sub');
            const card4Title = document.getElementById('kpiCard4Title');
            const card4Val = document.getElementById('kpiCard4Val');
            const card4Sub = document.getElementById('kpiCard4Sub');

            const monthsList = data.selected_months_list || availableMonths;

            if (currentViewMode === 'city') {
                // ==========================================
                // KPI CHẾ ĐỘ SO SÁNH TỈNH / THÀNH PHỐ
                // ==========================================
                card1Title.innerText = "Tổng Dòng Tỉnh / TP";
                card2Title.innerText = "Số Tỉnh / Thành Phố";
                const totalCities = (data.city_data || []).length;
                card2Val.innerText = totalCities;
                card2Sub.innerHTML = `<i class="fa-solid fa-map-pin text-sky-400"></i> Địa bàn ghi nhận hỗ trợ`;

                card3Title.innerText = "Top 1 Sản Lượng Tỉnh";
                if (data.city_data && data.city_data.length > 0) {
                    const topCityVol = [...data.city_data].sort((a, b) => b.count - a.count)[0];
                    card3Val.innerText = topCityVol.name.replace('Tỉnh ', '').replace('Thành phố ', 'TP. ');
                    card3Sub.innerHTML = `<i class="fa-solid fa-fire text-amber-400"></i> ${topCityVol.count.toLocaleString('vi-VN')} dòng (${topCityVol.impact_rate}% impact)`;
                }

                card4Title.innerText = "Tỷ Lệ Impact Toàn Bộ Tỉnh";
                card4Val.innerText = `${data.team_impact_rate || 0}%`;
                if (data.city_data && data.city_data.length > 0) {
                    const qualified = data.city_data.filter(c => c.count >= 20);
                    const topCityRate = (qualified.length > 0 ? qualified : data.city_data).sort((a, b) => b.impact_rate - a.impact_rate)[0];
                    card4Sub.innerHTML = `<i class="fa-solid fa-trophy text-emerald-400"></i> Top 1: ${topCityRate.name.replace('Tỉnh ', '').replace('Thành phố ', 'TP. ')} (${topCityRate.impact_rate}%)`;
                }

            } else if (currentViewMode === 'compare') {
                // CHẾ ĐỘ SO SÁNH TỪNG THÁNG
                card1Title.innerText = "Tổng Dòng Các Tháng Chọn";

                if (monthsList.length >= 2) {
                    const latestM = monthsList[monthsList.length - 1];
                    const firstM = monthsList[0];
                    
                    let latest1 = 0, latestTotal = 0, first1 = 0, firstTotal = 0;
                    rawRecords.forEach(r => {
                        if (r.month === latestM) {
                            latestTotal++;
                            if (r.impact === 1) latest1++;
                        }
                        if (r.month === firstM) {
                            firstTotal++;
                            if (r.impact === 1) first1++;
                        }
                    });
                    const latestRate = latestTotal > 0 ? +(latest1 * 100 / latestTotal).toFixed(1) : 0;
                    const firstRate = firstTotal > 0 ? +(first1 * 100 / firstTotal).toFixed(1) : 0;
                    const momDelta = +(latestRate - firstRate).toFixed(1);

                    card2Title.innerText = `Impact Tháng ${latestM} (Mới Nhất)`;
                    card2Val.innerText = `${latestRate}%`;
                    card2Sub.innerHTML = `<i class="fa-solid fa-layer-group text-emerald-400"></i> ${latest1.toLocaleString('vi-VN')} / ${latestTotal.toLocaleString('vi-VN')} dòng`;

                    card3Title.innerText = `Impact Tháng ${firstM} (Đầu Kỳ)`;
                    card3Val.innerText = `${firstRate}%`;
                    card3Sub.innerHTML = `<i class="fa-solid fa-clock-rotate-left text-slate-400"></i> ${first1.toLocaleString('vi-VN')} / ${firstTotal.toLocaleString('vi-VN')} dòng`;

                    card4Title.innerText = `Biến Động T${latestM} vs T${firstM}`;
                    if (momDelta > 0) {
                        card4Val.innerHTML = `<span class="text-emerald-400">+${momDelta}% ↗</span>`;
                        card4Sub.innerHTML = `<i class="fa-solid fa-arrow-trend-up text-emerald-400"></i> Tăng trưởng so với T${firstM}`;
                    } else if (momDelta < 0) {
                        card4Val.innerHTML = `<span class="text-rose-400">${momDelta}% ↘</span>`;
                        card4Sub.innerHTML = `<i class="fa-solid fa-arrow-trend-down text-rose-400"></i> Giảm so với T${firstM}`;
                    } else {
                        card4Val.innerHTML = `<span class="text-amber-300">0.0% ➔</span>`;
                        card4Sub.innerHTML = `<i class="fa-solid fa-arrow-right text-amber-300"></i> Không đổi`;
                    }
                } else {
                    const onlyM = monthsList[0] || '';
                    card2Title.innerText = "Có Impact (Số 1)";
                    card2Val.innerText = (data.total_impact1 || 0).toLocaleString('vi-VN');
                    card2Sub.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> Tháng ${onlyM}`;

                    card3Title.innerText = "Không Impact (Số 0)";
                    card3Val.innerText = (data.total_impact0 || 0).toLocaleString('vi-VN');
                    card3Sub.innerHTML = `<i class="fa-solid fa-circle-xmark text-rose-400"></i> Tháng ${onlyM}`;

                    card4Title.innerText = `Tỷ Lệ Impact Tháng ${onlyM}`;
                    card4Val.innerText = `${data.team_impact_rate || 0}%`;
                    card4Sub.innerHTML = `<i class="fa-solid fa-info-circle text-blue-400"></i> Chọn thêm tháng để so sánh MoM`;
                }
            } else if (currentViewMode === 'impact') {
                // CHẾ ĐỘ BÁO CÁO TỶ LỆ IMPACT %
                card1Title.innerText = "Tổng Số Dòng";
                card2Title.innerText = "Có Impact (Số 1)";
                card2Val.innerText = (data.total_impact1 || 0).toLocaleString('vi-VN');
                const imp1Pct = data.total_rows > 0 ? ((data.total_impact1 * 100) / data.total_rows).toFixed(1) : 0;
                card2Sub.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> ${imp1Pct}% tổng lượt hỗ trợ`;

                card3Title.innerText = "Không Impact (Số 0)";
                card3Val.innerText = (data.total_impact0 || 0).toLocaleString('vi-VN');
                const imp0Pct = data.total_rows > 0 ? ((data.total_impact0 * 100) / data.total_rows).toFixed(1) : 0;
                card3Sub.innerHTML = `<i class="fa-solid fa-circle-xmark text-rose-400"></i> ${imp0Pct}% chưa tạo impact`;

                card4Title.innerText = "Tỷ Lệ Impact Toàn Team";
                card4Val.innerText = `${data.team_impact_rate || 0}%`;

                if (data.staff_data && data.staff_data.length > 0) {
                    const topImpact = [...data.staff_data].sort((a, b) => b.impact_rate - a.impact_rate)[0];
                    card4Sub.innerHTML = `<i class="fa-solid fa-trophy text-amber-400"></i> Top 1: ${parseShortName(topImpact.name)} (${topImpact.impact_rate}%)`;
                }
            } else {
                // CHẾ ĐỘ KHỐI LƯỢNG DÒNG (VOLUME)
                card1Title.innerText = "Tổng Số Dòng";
                card2Title.innerText = "Tổng Số Nhân Sự";
                card2Val.innerText = data.total_staff || 0;
                card2Sub.innerHTML = `<i class="fa-solid fa-users text-indigo-400"></i> Nhân sự ghi nhận xử lý`;

                card3Title.innerText = "Top 1 Sản Lượng";
                if (data.staff_data && data.staff_data.length > 0) {
                    const topVolume = [...data.staff_data].sort((a, b) => b.count - a.count)[0];
                    card3Val.innerText = parseShortName(topVolume.name);
                    card3Sub.innerHTML = `<i class="fa-solid fa-fire text-amber-400"></i> ${topVolume.count.toLocaleString('vi-VN')} dòng (${topVolume.percentage}%)`;
                }

                card4Title.innerText = "Trung Bình / Nhân Sự";
                const avg = data.total_staff > 0 ? Math.round(data.total_rows / data.total_staff) : 0;
                card4Val.innerText = avg.toLocaleString('vi-VN');
                card4Sub.innerHTML = `<i class="fa-solid fa-calculator text-emerald-400"></i> Dòng / 1 người`;
            }
        }

        // Vẽ biểu đồ trực quan (Live Action)
        function renderChart() {
            const ctx = document.getElementById('staffChart').getContext('2d');
            if (chartInstance) {
                chartInstance.destroy();
            }

            const staffList = (currentData.staff_data || []).slice(0, 10);
            const cityList = currentData.city_data || [];
            const labels = staffList.map(s => parseShortName(s.name));
            const activeMonths = currentData.selected_months_list || Array.from(selectedMonths).sort((a,b) => parseInt(a)-parseInt(b));

            if (currentViewMode === 'city') {
                // ==========================================
                // 1. CHẾ ĐỘ SO SÁNH TỈNH / THÀNH PHỐ (BIỂU ĐỒ CỘT NGANG)
                // ==========================================
                const topCities = cityList.slice(0, 15);
                const cityLabels = topCities.map(c => c.name.replace('Tỉnh ', '').replace('Thành phố ', 'TP. '));
                const cityRates = topCities.map(c => c.impact_rate);
                const cityCounts = topCities.map(c => c.count);

                if (currentChartType === 'bar') {
                    chartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: cityLabels,
                            datasets: [{
                                label: currentSortMode === 'rate' ? 'Tỷ lệ Impact (%)' : 'Số lượng dòng',
                                data: currentSortMode === 'rate' ? cityRates : cityCounts,
                                backgroundColor: topCities.map(c => getImpactColor(c.impact_rate).bg),
                                borderRadius: 6,
                                borderSkipped: false
                            }]
                        },
                        options: {
                            indexAxis: 'y', // Biểu đồ cột ngang
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        title: function(items) {
                                            const idx = items[0].dataIndex;
                                            return topCities[idx].name;
                                        },
                                        label: function(ctx) {
                                            const item = topCities[ctx.dataIndex];
                                            return ` Tỷ lệ Impact: ${item.impact_rate}%`;
                                        },
                                        afterLabel: function(ctx) {
                                            const item = topCities[ctx.dataIndex];
                                            return `Có Impact (1): ${item.impact1.toLocaleString('vi-VN')} dòng\nKhông Impact (0): ${item.impact0.toLocaleString('vi-VN')} dòng\nTổng lượt: ${item.count.toLocaleString('vi-VN')} dòng (${item.percentage}% thị phần)`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    min: 0,
                                    max: currentSortMode === 'rate' ? 100 : undefined,
                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                    ticks: {
                                        color: '#94a3b8',
                                        callback: function(v) { return currentSortMode === 'rate' ? v + '%' : v.toLocaleString('vi-VN'); }
                                    }
                                },
                                y: {
                                    grid: { display: false },
                                    ticks: {
                                        color: '#f8fafc',
                                        font: { size: 11, weight: '600' }
                                    }
                                }
                            }
                        }
                    });
                } else {
                    const topDoughnut = cityList.slice(0, 10);
                    chartInstance = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: topDoughnut.map(c => c.name.replace('Tỉnh ', '').replace('Thành phố ', 'TP. ')),
                            datasets: [{
                                data: topDoughnut.map(c => c.count),
                                backgroundColor: [
                                    '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899',
                                    '#06b6d4', '#f97316', '#6366f1', '#14b8a6', '#64748b'
                                ],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'right', labels: { color: '#cbd5e1', font: { size: 11 }, boxWidth: 12 } }
                            }
                        }
                    });
                }

            } else if (currentViewMode === 'compare') {
                // ==========================================
                // 2. CHẾ ĐỘ SO SÁNH TỪNG THÁNG (MoM)
                // ==========================================
                if (currentChartType === 'bar') {
                    const datasets = activeMonths.map((m, idx) => {
                        const col = getMonthColor(m, idx);
                        return {
                            label: `Tháng ${m}`,
                            data: staffList.map(s => (s.months && s.months[m]) ? s.months[m].rate : 0),
                            backgroundColor: col.bg,
                            borderColor: col.border,
                            borderWidth: 1,
                            borderRadius: 6,
                            borderSkipped: false
                        };
                    });

                    chartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top',
                                    labels: { color: '#cbd5e1', font: { size: 11, weight: 'bold' }, boxWidth: 14 }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const m = activeMonths[ctx.datasetIndex];
                                            const staff = staffList[ctx.dataIndex];
                                            const mData = (staff.months && staff.months[m]) ? staff.months[m] : null;
                                            if (mData) {
                                                return ` Tháng ${m}: ${mData.rate}% (${mData.impact1}/${mData.count} dòng có impact)`;
                                            }
                                            return ` Tháng ${m}: Không có dữ liệu`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { color: '#94a3b8', font: { size: 10 } }
                                },
                                y: {
                                    min: 0,
                                    max: 100,
                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                    ticks: {
                                        color: '#94a3b8',
                                        callback: function(v) { return v + '%'; }
                                    }
                                }
                            }
                        }
                    });
                } else {
                    const topPerformers = staffList.slice(0, 6);
                    const staffPalette = ['#10b981', '#38bdf8', '#818cf8', '#f59e0b', '#ec4899', '#f43f5e'];

                    const datasets = topPerformers.map((s, idx) => {
                        const col = staffPalette[idx % staffPalette.length];
                        return {
                            label: parseShortName(s.name),
                            data: activeMonths.map(m => (s.months && s.months[m]) ? s.months[m].rate : null),
                            borderColor: col,
                            backgroundColor: col,
                            tension: 0.3,
                            fill: false,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            spanGaps: true
                        };
                    });

                    chartInstance = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: activeMonths.map(m => `Tháng ${m}`),
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top',
                                    labels: { color: '#cbd5e1', font: { size: 11 }, boxWidth: 12 }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            return ` ${ctx.dataset.label}: ${ctx.parsed.y}%`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                    ticks: { color: '#94a3b8', font: { size: 11, weight: 'bold' } }
                                },
                                y: {
                                    min: 0,
                                    max: 100,
                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                    ticks: {
                                        color: '#94a3b8',
                                        callback: function(v) { return v + '%'; }
                                    }
                                }
                            }
                        }
                    });
                }

            } else if (currentViewMode === 'impact') {
                // ==========================================
                // 3. CHẾ ĐỘ BIỂU ĐỒ IMPACT CHUẨN
                // ==========================================
                if (currentChartType === 'bar') {
                    const rates = staffList.map(s => s.impact_rate);
                    chartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Tỷ lệ Impact (%)',
                                data: rates,
                                backgroundColor: staffList.map(s => getImpactColor(s.impact_rate).bg),
                                borderRadius: 8,
                                borderSkipped: false
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const item = staffList[ctx.dataIndex];
                                            return `Tỷ lệ Impact: ${item.impact_rate}%`;
                                        },
                                        afterLabel: function(ctx) {
                                            const item = staffList[ctx.dataIndex];
                                            return `Có Impact (1): ${item.impact1.toLocaleString('vi-VN')} dòng\nKhông Impact (0): ${item.impact0.toLocaleString('vi-VN')} dòng\nTổng xử lý: ${item.count.toLocaleString('vi-VN')} dòng`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { color: '#94a3b8', font: { size: 10 } }
                                },
                                y: {
                                    min: 0,
                                    max: 100,
                                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                                    ticks: {
                                        color: '#94a3b8',
                                        callback: function(v) { return v + '%'; }
                                    }
                                }
                            }
                        }
                    });
                } else {
                    const total1 = currentData.total_impact1 || 0;
                    const total0 = currentData.total_impact0 || 0;
                    chartInstance = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Có Impact (Số 1)', 'Không Impact (Số 0)'],
                            datasets: [{
                                data: [total1, total0],
                                backgroundColor: ['#10b981', '#f43f5e'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: { color: '#cbd5e1', font: { size: 11 }, boxWidth: 14 }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            const total = total1 + total0;
                                            const val = ctx.parsed;
                                            const pct = total > 0 ? ((val * 100) / total).toFixed(1) : 0;
                                            return ` ${ctx.label}: ${val.toLocaleString('vi-VN')} dòng (${pct}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            } else {
                // ==========================================
                // 4. CHẾ ĐỘ BIỂU ĐỒ KHỐI LƯỢNG (VOLUME)
                // ==========================================
                const counts = staffList.map(s => s.count);
                if (currentChartType === 'bar') {
                    chartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Số lượng dòng',
                                data: counts,
                                backgroundColor: staffList.map((_, i) => {
                                    if (i === 0) return '#f59e0b';
                                    if (i === 1) return '#94a3b8';
                                    if (i === 2) return '#d97706';
                                    return '#3b82f6';
                                }),
                                borderRadius: 8,
                                borderSkipped: false
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        afterLabel: function(ctx) {
                                            const item = staffList[ctx.dataIndex];
                                            return `Tỷ trọng: ${item.percentage}%\nCó Impact: ${item.impact1} dòng (${item.impact_rate}%)\nĐã làm: ${item.done} dòng`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
                                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } }
                            }
                        }
                    });
                } else {
                    chartInstance = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: labels,
                            datasets: [{
                                data: counts,
                                backgroundColor: [
                                    '#3b82f6', '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
                                    '#f97316', '#eab308', '#10b981', '#14b8a6', '#06b6d4',
                                    '#0ea5e9', '#64748b'
                                ],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'right', labels: { color: '#cbd5e1', font: { size: 11 }, boxWidth: 12 } }
                            }
                        }
                    });
                }
            }
        }

        // Render Bảng xếp hạng chi tiết (Tự thích ứng theo View Mode)
        function renderTable(items) {
            const thead = document.getElementById('tableHead');
            const tbody = document.getElementById('staffTableBody');
            tbody.innerHTML = '';
            document.getElementById('tableCountBadge').innerText = items.length;

            const activeMonths = currentData.selected_months_list || Array.from(selectedMonths).sort((a,b) => parseInt(a)-parseInt(b));

            if (currentViewMode === 'city') {
                // ==========================================
                // HEADER & ROWS CHO CHẾ ĐỘ TỈNH / THÀNH PHỐ
                // ==========================================
                thead.innerHTML = `
                    <tr>
                        <th class="py-2.5 px-2 text-center w-8">#</th>
                        <th class="py-2.5 px-2">Tỉnh / Thành phố</th>
                        <th class="py-2.5 px-2 text-right">Tổng dòng</th>
                        <th class="py-2.5 px-2 text-right text-emerald-400">Có (1)</th>
                        <th class="py-2.5 px-2 text-right text-rose-400">Không (0)</th>
                        <th class="py-2.5 px-2.5 text-right text-amber-300">% Impact</th>
                    </tr>
                `;

                items.forEach((item) => {
                    let badgeRank = `<span class="text-slate-400 font-bold">${item.rank}</span>`;
                    if (item.rank === 1) badgeRank = `<span class="text-base">🥇</span>`;
                    if (item.rank === 2) badgeRank = `<span class="text-base">🥈</span>`;
                    if (item.rank === 3) badgeRank = `<span class="text-base">🥉</span>`;

                    const colorInfo = getImpactColor(item.impact_rate);

                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-slate-800/40 transition group";
                    tr.innerHTML = `
                        <td class="py-2.5 px-2 text-center">${badgeRank}</td>
                        <td class="py-2.5 px-2">
                            <div class="font-bold text-white text-xs group-hover:text-sky-400 transition flex items-center gap-1.5 truncate max-w-[150px]">
                                <i class="fa-solid fa-location-dot text-sky-400 text-[10px]"></i>
                                <span>${item.name}</span>
                            </div>
                            <div class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[150px]">Chiếm ${item.percentage}% sản lượng</div>
                        </td>
                        <td class="py-2.5 px-2 text-right text-slate-200 font-semibold text-xs">
                            ${item.count.toLocaleString('vi-VN')}
                        </td>
                        <td class="py-2.5 px-2 text-right">
                            <span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                +${item.impact1.toLocaleString('vi-VN')}
                            </span>
                        </td>
                        <td class="py-2.5 px-2 text-right">
                            <span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                ${item.impact0.toLocaleString('vi-VN')}
                            </span>
                        </td>
                        <td class="py-2.5 px-2.5 text-right">
                            <span class="font-bold text-xs ${colorInfo.text}">${item.impact_rate}%</span>
                            <div class="w-14 bg-slate-800 rounded-full h-1.5 ml-auto mt-0.5 overflow-hidden border border-slate-700/50">
                                <div class="h-full rounded-full" style="width: ${item.impact_rate}%; background-color: ${colorInfo.bg}"></div>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

            } else if (currentViewMode === 'compare') {
                // ==========================================
                // HEADER & ROWS CHO CHẾ ĐỘ SO SÁNH MA TRẬN THÁNG
                // ==========================================
                let monthHeaders = '';
                activeMonths.forEach((m, idx) => {
                    const col = getMonthColor(m, idx).solid;
                    monthHeaders += `<th class="py-2.5 px-2 text-center" style="color: ${col}">T${m}</th>`;
                });

                thead.innerHTML = `
                    <tr>
                        <th class="py-2.5 px-2 text-center w-8">#</th>
                        <th class="py-2.5 px-2">Nhân sự</th>
                        ${monthHeaders}
                        <th class="py-2.5 px-2 text-right text-amber-300">TB Kỳ</th>
                        <th class="py-2.5 px-2 text-center">MoM</th>
                    </tr>
                `;

                items.forEach((item) => {
                    let badgeRank = `<span class="text-slate-400 font-bold">${item.rank}</span>`;
                    if (item.rank === 1) badgeRank = `<span class="text-base">🥇</span>`;
                    if (item.rank === 2) badgeRank = `<span class="text-base">🥈</span>`;
                    if (item.rank === 3) badgeRank = `<span class="text-base">🥉</span>`;

                    const shortName = parseShortName(item.name);
                    const parts = (item.name || '').split(' - ');
                    const code = parts[0] || '';
                    const branch = parts[parts.length - 1] || '';
                    const avgColor = getImpactColor(item.impact_rate);

                    let monthCells = '';
                    activeMonths.forEach((m) => {
                        const mData = item.months ? item.months[m] : null;
                        if (mData && mData.count > 0) {
                            const cInfo = getImpactColor(mData.rate);
                            monthCells += `
                                <td class="py-2.5 px-2 text-center">
                                    <span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-bold ${cInfo.badge}" title="Có impact: ${mData.impact1}/${mData.count} dòng">
                                        ${mData.rate}%
                                    </span>
                                </td>
                            `;
                        } else {
                            monthCells += `<td class="py-2.5 px-2 text-center text-slate-600 font-mono">-</td>`;
                        }
                    });

                    let trendBadge = `<span class="text-slate-500 font-mono text-[11px]">-</span>`;
                    if (item.delta !== null && item.delta !== undefined) {
                        if (item.delta > 0) {
                            trendBadge = `<span class="text-emerald-400 font-bold text-[11px]"><i class="fa-solid fa-arrow-trend-up"></i> +${item.delta}%</span>`;
                        } else if (item.delta < 0) {
                            trendBadge = `<span class="text-rose-400 font-bold text-[11px]"><i class="fa-solid fa-arrow-trend-down"></i> ${item.delta}%</span>`;
                        } else {
                            trendBadge = `<span class="text-slate-400 font-medium text-[11px]"><i class="fa-solid fa-arrow-right"></i> 0.0%</span>`;
                        }
                    }

                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-slate-800/40 transition group";
                    tr.innerHTML = `
                        <td class="py-2.5 px-2 text-center">${badgeRank}</td>
                        <td class="py-2.5 px-2">
                            <div class="font-bold text-white text-xs group-hover:text-blue-400 transition truncate max-w-[130px]">${shortName}</div>
                            <div class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[130px]">${code} • ${branch}</div>
                        </td>
                        ${monthCells}
                        <td class="py-2.5 px-2 text-right">
                            <span class="font-bold text-xs ${avgColor.text}">${item.impact_rate}%</span>
                        </td>
                        <td class="py-2.5 px-2 text-center">
                            ${trendBadge}
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

            } else {
                // ==========================================
                // HEADER & ROWS CHO CHẾ ĐỘ TIÊU CHUẨN (IMPACT / VOLUME)
                // ==========================================
                thead.innerHTML = `
                    <tr>
                        <th class="py-2.5 px-2 text-center w-8">#</th>
                        <th class="py-2.5 px-2">Nhân sự</th>
                        <th class="py-2.5 px-2 text-right">Tổng</th>
                        <th class="py-2.5 px-2 text-right text-emerald-400">Có (1)</th>
                        <th class="py-2.5 px-2 text-right text-rose-400">Không (0)</th>
                        <th class="py-2.5 px-2.5 text-right text-amber-300">% Impact</th>
                    </tr>
                `;

                items.forEach((item) => {
                    let badgeRank = `<span class="text-slate-400 font-bold">${item.rank}</span>`;
                    if (item.rank === 1) badgeRank = `<span class="text-base">🥇</span>`;
                    if (item.rank === 2) badgeRank = `<span class="text-base">🥈</span>`;
                    if (item.rank === 3) badgeRank = `<span class="text-base">🥉</span>`;

                    const shortName = parseShortName(item.name);
                    const parts = (item.name || '').split(' - ');
                    const code = parts[0] || '';
                    const branch = parts[parts.length - 1] || '';
                    const colorInfo = getImpactColor(item.impact_rate);

                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-slate-800/40 transition group";
                    
                    tr.innerHTML = `
                        <td class="py-2.5 px-2 text-center">${badgeRank}</td>
                        <td class="py-2.5 px-2">
                            <div class="font-bold text-white text-xs group-hover:text-blue-400 transition truncate max-w-[150px]">${shortName}</div>
                            <div class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[150px]">${code} • ${branch}</div>
                        </td>
                        <td class="py-2.5 px-2 text-right text-slate-200 font-semibold text-xs">
                            ${item.count.toLocaleString('vi-VN')}
                        </td>
                        <td class="py-2.5 px-2 text-right">
                            <span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                +${item.impact1.toLocaleString('vi-VN')}
                            </span>
                        </td>
                        <td class="py-2.5 px-2 text-right">
                            <span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                ${item.impact0.toLocaleString('vi-VN')}
                            </span>
                        </td>
                        <td class="py-2.5 px-2.5 text-right">
                            <span class="font-bold text-xs ${colorInfo.text}">${item.impact_rate}%</span>
                            <div class="w-14 bg-slate-800 rounded-full h-1.5 ml-auto mt-0.5 overflow-hidden border border-slate-700/50">
                                <div class="h-full rounded-full" style="width: ${item.impact_rate}%; background-color: ${colorInfo.bg}"></div>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

        // Chuyển đổi chế độ xem (Impact vs Volume vs Compare vs City)
        function setViewMode(mode) {
            currentViewMode = mode;
            const btnImpact = document.getElementById('modeImpactBtn');
            const btnVolume = document.getElementById('modeVolumeBtn');
            const btnCompare = document.getElementById('modeCompareBtn');
            const btnCity = document.getElementById('modeCityBtn');
            const chartTitleText = document.getElementById('chartTitleText');
            const chartTitleIcon = document.getElementById('chartTitleIcon');
            const chartSubTitle = document.getElementById('chartSubTitle');
            const tableMainTitle = document.getElementById('tableMainTitle');
            const tableHeaderIcon = document.getElementById('tableHeaderIcon');
            const chartLegendGuide = document.getElementById('chartLegendGuide');
            const btnBar = document.getElementById('btnBarChart');
            const btnSec = document.getElementById('btnSecondaryChart');
            const searchInput = document.getElementById('searchInput');

            const inactiveClass = "px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition flex items-center gap-1.5";
            const activeClass = "px-3 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow transition flex items-center gap-1.5";

            btnImpact.className = inactiveClass;
            btnVolume.className = inactiveClass;
            btnCompare.className = inactiveClass;
            btnCity.className = inactiveClass;

            if (mode === 'city') {
                btnCity.className = activeClass;
                chartTitleText.innerText = "So Sánh Tỷ Lệ Impact (%) Theo Tỉnh / Thành Phố";
                chartTitleIcon.className = "fa-solid fa-map-location-dot text-sky-400";
                chartSubTitle.innerText = "Biểu đồ cột ngang so sánh % công việc thành công giữa các địa bàn";
                tableMainTitle.innerText = "Bảng Xếp Hạng Tỉnh / Thành Phố";
                tableHeaderIcon.className = "fa-solid fa-city text-sky-400";
                if (btnBar) btnBar.innerText = "Cột Ngang";
                if (btnSec) btnSec.innerText = "Tròn (Thị Phần)";
                if (searchInput) searchInput.placeholder = "Tìm nhanh theo tên tỉnh thành...";
                if (chartLegendGuide) chartLegendGuide.classList.remove('hidden');
            } else if (mode === 'compare') {
                btnCompare.className = activeClass;
                chartTitleText.innerText = "So Sánh Tỷ Lệ Impact Từng Tháng (MoM)";
                chartTitleIcon.className = "fa-solid fa-chart-line text-emerald-400";
                chartSubTitle.innerText = "Phân tích biến động và hiệu quả công việc giữa các tháng được chọn";
                tableMainTitle.innerText = "Ma Trận So Sánh Từng Tháng";
                tableHeaderIcon.className = "fa-solid fa-table-cells text-emerald-400";
                if (btnBar) btnBar.innerText = "Cột Nhóm";
                if (btnSec) btnSec.innerText = "Đường Trend";
                if (searchInput) searchInput.placeholder = "Tìm nhanh theo tên hoặc mã nhân viên...";
                if (chartLegendGuide) chartLegendGuide.classList.remove('hidden');
            } else if (mode === 'impact') {
                btnImpact.className = activeClass;
                chartTitleText.innerText = "Tỷ Lệ Impact (%) Theo Nhân Sự";
                chartTitleIcon.className = "fa-solid fa-bullseye text-blue-400";
                chartSubTitle.innerText = "So sánh % công việc thành công (impact = 1) giữa các nhân sự";
                tableMainTitle.innerText = "Bảng Xếp Hạng Tỷ Lệ Impact";
                tableHeaderIcon.className = "fa-solid fa-list-ol text-emerald-400";
                if (btnBar) btnBar.innerText = "Cột";
                if (btnSec) btnSec.innerText = "Tròn";
                if (searchInput) searchInput.placeholder = "Tìm nhanh theo tên hoặc mã nhân viên...";
                if (chartLegendGuide) chartLegendGuide.classList.remove('hidden');
            } else {
                btnVolume.className = activeClass;
                chartTitleText.innerText = "Xếp Hạng Số Lượng Dòng Theo Nhân Sự";
                chartTitleIcon.className = "fa-solid fa-ranking-star text-blue-400";
                chartSubTitle.innerText = "Biểu đồ so sánh sản lượng công việc giữa các nhân sự";
                tableMainTitle.innerText = "Bảng Thống Kê Sản Lượng";
                tableHeaderIcon.className = "fa-solid fa-chart-column text-indigo-400";
                if (btnBar) btnBar.innerText = "Cột";
                if (btnSec) btnSec.innerText = "Tròn";
                if (searchInput) searchInput.placeholder = "Tìm nhanh theo tên hoặc mã nhân viên...";
                if (chartLegendGuide) chartLegendGuide.classList.add('hidden');
            }

            applyFilters();
        }

        // Chuyển đổi sắp xếp (% Impact vs Số dòng)
        function setSortMode(sort) {
            currentSortMode = sort;
            const btnRate = document.getElementById('btnSortRate');
            const btnVol = document.getElementById('btnSortVolume');

            if (sort === 'rate') {
                btnRate.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition";
                btnVol.className = "px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition";
            } else {
                btnVol.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition";
                btnRate.className = "px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition";
            }

            applyFilters();
        }

        // Đổi loại biểu đồ (Cột / Tròn hoặc Cột Nhóm / Đường Trend)
        function setChartType(type) {
            currentChartType = type;
            const btnBar = document.getElementById('btnBarChart');
            const btnSec = document.getElementById('btnSecondaryChart');

            btnBar.className = (type === 'bar')
                ? 'px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white transition'
                : 'px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';

            btnSec.className = (type === 'secondary')
                ? 'px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white transition'
                : 'px-3 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition';

            renderChart();
        }

        // Đặt lại các bộ lọc về mặc định
        function resetFilters() {
            selectedMonths = new Set(availableMonths);
            renderMonthPills();

            const d = document.getElementById('filterDay');
            const c = document.getElementById('filterCity');
            const s = document.getElementById('searchInput');
            if (d) d.value = '';
            if (c) c.value = '';
            if (s) s.value = '';
            applyFilters();
        }

        // Xử lý dữ liệu trả về từ Apps Script Web App
        function processAppsScriptData(resp, currentSheetName) {
            let rows = [];
            if (resp && resp.data && Array.isArray(resp.data)) {
                rows = resp.data;
            } else if (Array.isArray(resp)) {
                rows = resp;
            }

            if (!rows || rows.length === 0) return null;

            // KIỂM TRA 1: Nếu là dữ liệu dạng Pivot Table
            if (rows.length >= 2 && Array.isArray(rows[0]) && rows[0].length <= 5) {
                const sampleVal = String(rows[1][1] !== undefined ? rows[1][1] : '').trim().replace(/,/g, '');
                if (sampleVal !== '' && !isNaN(Number(sampleVal))) {
                    const staffCounts = {};
                    let total = 0;
                    for (let i = 1; i < rows.length; i++) {
                        const r = rows[i];
                        if (!r || r.length < 2) continue;
                        const name = (r[0] || '').toString().trim();
                        const valStr = String(r[1] !== undefined ? r[1] : '').trim().replace(/,/g, '');
                        const countVal = Number(valStr);
                        const lower = name.toLowerCase();
                        if (!name || lower.includes('grand total') || lower.includes('tổng cộng') || lower.includes('total') || isNaN(countVal)) {
                            continue;
                        }
                        staffCounts[name] = countVal;
                        total += countVal;
                    }
                    if (Object.keys(staffCounts).length > 0) {
                        const staffData = Object.entries(staffCounts)
                            .sort((a, b) => b[1] - a[1])
                            .map(([name, count], idx) => ({
                                rank: idx + 1,
                                name: name,
                                count: count,
                                impact1: count,
                                impact0: 0,
                                impact_rate: 100,
                                percentage: total > 0 ? +(count * 100 / total).toFixed(2) : 0,
                                done: count
                            }));
                        
                        rawRecords = [];
                        currentData = {
                            tab_name: currentSheetName || resp.sheet_name || "Pivot Table",
                            total_rows: total,
                            total_impact1: total,
                            total_impact0: 0,
                            team_impact_rate: 100,
                            total_staff: staffData.length,
                            staff_data: staffData,
                            city_data: []
                        };
                        applyFilters();
                        return currentData;
                    }
                }
            }

            // KIỂM TRA 2: Bảng chi tiết gốc (A:X với 24 cột)
            const headerRow = rows[0].map(h => (h || '').toString().trim());
            let staffColIdx = headerRow.indexOf('Người xử lý');
            if (staffColIdx === -1) {
                staffColIdx = headerRow.findIndex(h => h.includes('Người xử lý') || h.toLowerCase().includes('nhân sự') || h.toLowerCase().includes('người tạo'));
            }
            if (staffColIdx === -1) staffColIdx = 17;

            let statusColIdx = headerRow.indexOf('Tình trạng xử lý');
            let impactColIdx = headerRow.indexOf('impact');
            let cityColIdx = headerRow.indexOf('Tỉnh/Thành phố');
            let monthColIdx = headerRow.indexOf('Tháng');
            let dayColIdx = headerRow.indexOf('Ngày');

            const records = [];
            for (let i = 1; i < rows.length; i++) {
                const r = rows[i];
                if (!r || r.length <= staffColIdx) continue;
                const staffName = (r[staffColIdx] || '').toString().trim();
                if (!staffName || staffName === 'Người xử lý') continue;

                const impRaw = impactColIdx !== -1 && r[impactColIdx] !== undefined ? r[impactColIdx] : '';
                const isImpact = (impRaw === 1 || impRaw === '1' || impRaw === 1.0 || impRaw === '1.0');

                records.push({
                    staff: staffName,
                    city: (cityColIdx !== -1 && r[cityColIdx]) ? String(r[cityColIdx]).trim() : '',
                    month: (monthColIdx !== -1 && r[monthColIdx] !== undefined && r[monthColIdx] !== '') ? String(r[monthColIdx]).trim() : '',
                    day: (dayColIdx !== -1 && r[dayColIdx] !== undefined && r[dayColIdx] !== '') ? String(r[dayColIdx]).trim() : '',
                    status: (statusColIdx !== -1 && r[statusColIdx]) ? String(r[statusColIdx]).trim() : '',
                    impact: isImpact ? 1 : 0
                });
            }

            rawRecords = records;
            populateFilterDropdowns(records);
            applyFilters();

            return currentData;
        }

        // Tự động kéo Live Data với Tiến Độ % & Dung Lượng MB Trực Quan
        async function fetchImpactLiveOrReload() {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');

            if (currentModule === 'pctq') {
                await fetchPCTQLive(true);
                if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
                return;
            } else if (currentModule === 'hardware') {
                await fetchHardwareLive(true);
                if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
                return;
            }

            const sheet = 'tudaunam';
            const range = 'A1:X';
            const apiUrl = `${ENDPOINT_API_URL}?sheet=${encodeURIComponent(sheet)}&range=${encodeURIComponent(range)}`;

            // Giai đoạn 1: Giả lập tiến độ kết nối trong khi chờ Google Script phản hồi
            let connectProgress = 5;
            updateLoadingProgress(connectProgress, 'Đang kết nối Apps Script... 5%');
            const connectTimer = setInterval(() => {
                if (connectProgress < 18) {
                    connectProgress += 3;
                    updateLoadingProgress(connectProgress, `Đang chuẩn bị dữ liệu... ${connectProgress}%`);
                }
            }, 500);

            try {
                const res = await fetch(apiUrl, { redirect: 'follow' });
                clearInterval(connectTimer);

                if (!res.ok) throw new Error('HTTP ' + res.status);

                // Ước tính kích thước payload dựa trên lần tải trước hoặc mặc định ~18.5 MB
                const savedBytes = parseInt(localStorage.getItem('last_data_bytes'), 10);
                const expectedBytes = (savedBytes && savedBytes > 5000000) ? savedBytes : 18.5 * 1024 * 1024;

                const reader = res.body.getReader();
                const chunks = [];
                let receivedBytes = 0;
                let lastUpdate = Date.now();

                // Giai đoạn 2: Đọc streaming chunks và cập nhật % + MB theo thời gian thực
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    chunks.push(value);
                    receivedBytes += value.length;

                    const now = Date.now();
                    if (now - lastUpdate > 80) { // Cập nhật mượt mà mỗi 80ms
                        lastUpdate = now;
                        const mb = (receivedBytes / (1024 * 1024)).toFixed(1);
                        const totalMb = (expectedBytes / (1024 * 1024)).toFixed(1);
                        const downloadPct = Math.min(96, Math.max(20, Math.round(20 + (receivedBytes / expectedBytes) * 76)));
                        updateLoadingProgress(downloadPct, `Đang tải: ${mb}/${totalMb} MB (${downloadPct}%)`);
                    }
                }

                if (receivedBytes > 5000000) {
                    localStorage.setItem('last_data_bytes', receivedBytes);
                }

                // Giai đoạn 3: Ghép dữ liệu và phân tích
                updateLoadingProgress(98, 'Đang giải nén & xử lý 14.229 dòng... (98%)');

                const allBytes = new Uint8Array(receivedBytes);
                let offset = 0;
                for (const chunk of chunks) {
                    allBytes.set(chunk, offset);
                    offset += chunk.length;
                }

                const decoder = new TextDecoder('utf-8');
                const text = decoder.decode(allBytes);
                const json = JSON.parse(text);

                const parsed = processAppsScriptData(json, sheet);
                if (parsed && parsed.total_rows > 0) {
                    // Giai đoạn 4: Hoàn tất 100%
                    updateLoadingProgress(100, `Live API: ${parsed.total_rows.toLocaleString('vi-VN')} dòng (100% • ${new Date().toLocaleTimeString()})`, false, true);
                    if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
                    return;
                }
            } catch (e) {
                console.warn("Apps script stream fetch error:", e);
                clearInterval(connectTimer);
            }

            // Fallback: Sử dụng dữ liệu offline cache nếu mạng lỗi
            renderMonthPills();
            applyFilters();
            updateLoadingProgress(100, 'Dữ liệu Offline Cache', true, false);
            if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
        }

