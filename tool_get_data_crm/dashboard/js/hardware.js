// =============================================================================
// KIOTVIET CRM ANALYTICS - HARDWARE MODULE (hardware.js)
// Báo cáo Doanh thu & Hợp đồng phần cứng (Tab: phancung)
// =============================================================================
        let rawHardwareRecords = INITIAL_HARDWARE_RECORDS;
        let isHwFetched = false;
        let hwSelectedStaff = '';
        let hwSelectedStatus = '';
        let hwSearchQuery = '';
        let hwStaffSort = 'revenue'; // 'revenue' | 'orders' | 'rate' | 'total'
        let hwCurrentPage = 1;
        let hwPageSize = 15;
        let hwStaffChartInstance = null;
        let hwStatusChartInstance = null;

        // Tự động kéo dữ liệu tab phancung từ Apps Script
        async function fetchHardwareLive(force = false) {
            const icon = document.getElementById('refreshIcon');
            if (icon) icon.classList.add('fa-spin');

            updateLoadingProgress(15, 'Đang kết nối Apps Script phancung... 15%');
            const apiUrl = `${ENDPOINT_API_URL}?sheet=phancung`;

            try {
                const res = await fetch(apiUrl, { redirect: 'follow' });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                updateLoadingProgress(60, 'Đang phân tích 188 dòng phần cứng... 60%');

                const json = await res.json();
                if (json && json.status === 'success' && Array.isArray(json.data)) {
                    const rows = json.data;
                    const records = [];
                    for (let i = 1; i < rows.length; i++) {
                        const r = rows[i];
                        if (!r || r.length === 0) continue;
                        const amtStr = (r[3] || '0').toString().replace(/,/g, '').trim();
                        const amt = parseFloat(amtStr) || 0;
                        records.push({
                            id: r[0] || '',
                            contract_no: r[1] || '',
                            retailer_id: r[2] || '',
                            amount: amt,
                            created_at: r[4] || '',
                            store_name: r[5] || '',
                            opportunity: r[6] || '',
                            status: (r[7] || 'Không xác định').trim(),
                            staff: (r[8] || 'Chưa phân công').trim(),
                            updated_at: r[9] || ''
                        });
                    }

                    if (records.length > 0) {
                        rawHardwareRecords = records;
                        isHwFetched = true;
                        populateHardwareFilterDropdowns();
                        renderHardwareDashboard();
                        updateLoadingProgress(100, `Live API phancung: ${records.length} đơn (100% • ${new Date().toLocaleTimeString('vi-VN')})`, false, true);
                        if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
                        return;
                    }
                }
            } catch (err) {
                console.warn("fetchHardwareLive error:", err);
            }

            // Fallback
            isHwFetched = true;
            populateHardwareFilterDropdowns();
            renderHardwareDashboard();
            updateLoadingProgress(100, `Dữ liệu phancung (${rawHardwareRecords.length} đơn)`, true, false);
            if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
        }

        // Tạo các option cho bộ lọc Phần Cứng
        function populateHardwareFilterDropdowns() {
            const staffSel = document.getElementById('hwFilterStaff');
            const statusSel = document.getElementById('hwFilterStatus');
            if (!staffSel || !statusSel) return;

            const currentStaffVal = staffSel.value;
            const currentStatusVal = statusSel.value;

            const staffs = new Set();
            const statuses = new Set();

            rawHardwareRecords.forEach(r => {
                if ((r.staff || '').toLowerCase().includes('đã nghỉ')) return; // bỏ qua đã nghỉ
                if (r.staff) staffs.add(r.staff);
                if (r.status) statuses.add(r.status);
            });

            staffSel.innerHTML = '<option value="">Tất cả nhân sự (' + staffs.size + ')</option>';
            Array.from(staffs).sort().forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.innerText = s;
                if (s === currentStaffVal) opt.selected = true;
                staffSel.appendChild(opt);
            });

            statusSel.innerHTML = '<option value="">Tất cả trạng thái (' + statuses.size + ')</option>';
            Array.from(statuses).sort().forEach(st => {
                const opt = document.createElement('option');
                opt.value = st;
                opt.innerText = st;
                if (st === currentStatusVal) opt.selected = true;
                statusSel.appendChild(opt);
            });
        }

        // Áp dụng bộ lọc phần cứng
        function applyHardwareFilters() {
            const staffSel = document.getElementById('hwFilterStaff');
            const statusSel = document.getElementById('hwFilterStatus');
            const searchInp = document.getElementById('hwSearchInput');

            hwSelectedStaff = staffSel ? staffSel.value : '';
            hwSelectedStatus = statusSel ? statusSel.value : '';
            hwSearchQuery = searchInp ? searchInp.value.trim().toLowerCase() : '';
            hwCurrentPage = 1;

            renderHardwareDashboard();
        }

        // Đặt lại bộ lọc phần cứng
        function resetHardwareFilters() {
            const staffSel = document.getElementById('hwFilterStaff');
            const statusSel = document.getElementById('hwFilterStatus');
            const searchInp = document.getElementById('hwSearchInput');

            if (staffSel) staffSel.value = '';
            if (statusSel) statusSel.value = '';
            if (searchInp) searchInp.value = '';

            hwSelectedStaff = '';
            hwSelectedStatus = '';
            hwSearchQuery = '';
            hwCurrentPage = 1;

            renderHardwareDashboard();
        }

        // Sắp xếp bảng nhân sự phần cứng
        function setHwStaffSort(mode) {
            hwStaffSort = mode;
            const btnAmt = document.getElementById('btnHwSortAmt');
            const btnOrders = document.getElementById('btnHwSortOrders');

            if (btnAmt && btnOrders) {
                if (mode === 'revenue') {
                    btnAmt.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white transition";
                    btnOrders.className = "px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition";
                } else {
                    btnOrders.className = "px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white transition";
                    btnAmt.className = "px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition";
                }
            }

            renderHardwareDashboard();
        }

        // Chuyển trang bảng đơn hàng
        function changeHwPage(delta) {
            hwCurrentPage += delta;
            renderHardwareOrdersTable();
        }

        function setHwPageSize(size) {
            hwPageSize = parseInt(size, 10) || 15;
            hwCurrentPage = 1;
            renderHardwareOrdersTable();
        }

        // RENDER TOÀN BỘ DASHBOARD PHẦN CỨNG
        let lastFilteredHwRecords = [];

        function renderHardwareDashboard() {
            // Lọc dữ liệu (tự động loại nhân sự đã nghỉ)
            const filtered = rawHardwareRecords.filter(r => {
                if ((r.staff || '').toLowerCase().includes('đã nghỉ')) return false;
                if (hwSelectedStaff && r.staff !== hwSelectedStaff) return false;
                if (hwSelectedStatus && r.status !== hwSelectedStatus) return false;
                if (hwSearchQuery) {
                    const match = (r.contract_no || '').toLowerCase().includes(hwSearchQuery) ||
                                  (r.retailer_id || '').toLowerCase().includes(hwSearchQuery) ||
                                  (r.store_name || '').toLowerCase().includes(hwSearchQuery) ||
                                  (r.staff || '').toLowerCase().includes(hwSearchQuery);
                    if (!match) return false;
                }
                return true;
            });

            lastFilteredHwRecords = filtered;

            // Tính KPI tổng quan
            const totalOrders = filtered.length;
            let totalAmount = 0;
            let succOrders = 0;
            let succAmount = 0;

            const staffMap = {};
            const statusMap = {};

            filtered.forEach(r => {
                totalAmount += r.amount;
                const isSucc = (r.status === 'Thành công' || r.status === 'Đã chuyển nhượng');
                if (isSucc) {
                    succOrders++;
                    succAmount += r.amount;
                }

                // Nhóm theo nhân sự
                if (!staffMap[r.staff]) {
                    staffMap[r.staff] = {
                        name: r.staff,
                        total_orders: 0,
                        total_amount: 0,
                        succ_orders: 0,
                        succ_amount: 0,
                        sell_orders: 0,
                        transfer_orders: 0,
                        fail_orders: 0,
                        other_orders: 0
                    };
                }
                const sm = staffMap[r.staff];
                sm.total_orders++;
                sm.total_amount += r.amount;
                if (isSucc) {
                    sm.succ_orders++;
                    sm.succ_amount += r.amount;
                } else if (r.status === 'Bán hàng') {
                    sm.sell_orders++;
                } else if (r.status === 'KH chuyển nhượng' || r.status.toLowerCase().includes('chuyển nhượng')) {
                    sm.transfer_orders++;
                } else if (r.status.toLowerCase().includes('thất bại')) {
                    sm.fail_orders++;
                } else {
                    sm.other_orders++;
                }

                // Nhóm theo trạng thái
                if (!statusMap[r.status]) {
                    statusMap[r.status] = { count: 0, amount: 0 };
                }
                statusMap[r.status].count++;
                statusMap[r.status].amount += r.amount;
            });

            const succRate = totalOrders > 0 ? (succOrders * 100 / totalOrders).toFixed(1) : 0;

            // Xếp hạng nhân sự
            const staffList = Object.values(staffMap).map(s => {
                s.rate = s.total_orders > 0 ? (s.succ_orders * 100 / s.total_orders) : 0;
                // Rút gọn tên hiển thị trên chart
                const parts = s.name.split(' - ');
                s.shortName = parts.length >= 2 ? parts[1] : s.name;
                return s;
            });

            staffList.sort((a, b) => {
                if (hwStaffSort === 'revenue') return b.succ_amount - a.succ_amount;
                if (hwStaffSort === 'orders') return b.succ_orders - a.succ_orders;
                if (hwStaffSort === 'rate') return b.rate - a.rate;
                return b.total_orders - a.total_orders;
            });

            // Top staff
            const topStaff = staffList[0] || { name: 'Chưa có', succ_amount: 0, succ_orders: 0 };

            // 1. Cập nhật KPI Cards
            const elSuccAmt = document.getElementById('hwKpiSuccAmount');
            const elSuccAmtSub = document.getElementById('hwKpiSuccAmountSub');
            const elTotAmt = document.getElementById('hwKpiTotalAmount');
            const elTotAmtSub = document.getElementById('hwKpiTotalAmountSub');
            const elSuccRate = document.getElementById('hwKpiSuccRate');
            const elSuccRateSub = document.getElementById('hwKpiSuccRateSub');
            const elTopStaff = document.getElementById('hwKpiTopStaff');
            const elTopStaffSub = document.getElementById('hwKpiTopStaffSub');

            if (elSuccAmt) elSuccAmt.innerText = succAmount.toLocaleString('vi-VN') + ' ₫';
            if (elSuccAmtSub) elSuccAmtSub.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> ${succOrders.toLocaleString()} đơn chốt thành công (${succRate}%)`;

            if (elTotAmt) elTotAmt.innerText = totalAmount.toLocaleString('vi-VN') + ' ₫';
            if (elTotAmtSub) elTotAmtSub.innerHTML = `<i class="fa-solid fa-boxes-stacked text-blue-400"></i> Tổng ${totalOrders.toLocaleString()} hợp đồng phần cứng`;

            if (elSuccRate) elSuccRate.innerText = succRate + '%';
            if (elSuccRateSub) elSuccRateSub.innerHTML = `<i class="fa-solid fa-chart-pie text-amber-400"></i> ${succOrders} / ${totalOrders} đơn hoàn tất`;

            if (elTopStaff) elTopStaff.innerText = topStaff.shortName || topStaff.name;
            if (elTopStaffSub) elTopStaffSub.innerHTML = `<i class="fa-solid fa-coins text-emerald-400"></i> ${topStaff.succ_amount.toLocaleString('vi-VN')} ₫ (${topStaff.succ_orders} đơn TC)`;

            // 2. Cập nhật Banners
            const elSumText = document.getElementById('hwSummaryText');
            const elBSuccCount = document.getElementById('hwBannerSuccCount');
            const elBSuccAmt = document.getElementById('hwBannerSuccAmount');
            const elBTotAmt = document.getElementById('hwBannerTotalAmount');

            if (elSumText) elSumText.innerText = `Đang hiển thị ${filtered.length}/${rawHardwareRecords.length} đơn hàng hợp lệ`;
            if (elBSuccCount) elBSuccCount.innerText = succOrders.toLocaleString();
            if (elBSuccAmt) elBSuccAmt.innerText = succAmount.toLocaleString('vi-VN') + ' ₫';
            if (elBTotAmt) elBTotAmt.innerText = totalAmount.toLocaleString('vi-VN') + ' ₫';

            // 3. Render Chart 1: Doanh Thu Thành Công Theo Nhân Sự
            renderHwStaffChart(staffList);

            // 4. Render Chart 2: Cơ Cấu Trạng Thái Đơn Hàng
            renderHwStatusChart(statusMap, totalOrders, totalAmount);

            // 5. Render Bảng 1: Hiệu Suất Nhân Sự
            renderHwStaffTable(staffList, totalOrders, succOrders, succAmount, totalAmount);

            // 6. Render Bảng 2: Danh Sách Đơn Hàng Chi Tiết
            renderHardwareOrdersTable();
        }

        // Render Biểu đồ Horizontal Bar Doanh Thu Nhân Sự
        function renderHwStaffChart(staffList) {
            const ctx = document.getElementById('hwStaffChart');
            if (!ctx) return;

            if (hwStaffChartInstance) {
                hwStaffChartInstance.destroy();
            }

            const labels = staffList.map(s => s.shortName);
            const revenues = staffList.map(s => s.succ_amount);

            hwStaffChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Doanh thu Thành công (VNĐ)',
                        data: revenues,
                        backgroundColor: staffList.map((s, idx) => {
                            if (idx === 0) return 'rgba(16, 185, 129, 0.9)'; // Top 1 Emerald
                            if (idx === 1) return 'rgba(20, 184, 166, 0.85)'; // Top 2 Teal
                            if (idx === 2) return 'rgba(6, 182, 212, 0.85)';  // Top 3 Cyan
                            return 'rgba(59, 130, 246, 0.75)';                // Others Blue
                        }),
                        borderColor: staffList.map((s, idx) => idx === 0 ? '#10b981' : (idx === 1 ? '#14b8a6' : '#3b82f6')),
                        borderWidth: 1.5,
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            borderColor: 'rgba(51, 65, 85, 0.8)',
                            borderWidth: 1,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 12 },
                            padding: 12,
                            callbacks: {
                                title: (items) => {
                                    const idx = items[0].dataIndex;
                                    return staffList[idx].name;
                                },
                                label: (item) => {
                                    const idx = item.dataIndex;
                                    const s = staffList[idx];
                                    return [
                                        `💰 Doanh thu TC: ${s.succ_amount.toLocaleString('vi-VN')} ₫`,
                                        `📦 Số đơn thành công: ${s.succ_orders}/${s.total_orders} (${s.rate.toFixed(1)}%)`,
                                        `🏷️ Tổng giá trị tất cả đơn: ${s.total_amount.toLocaleString('vi-VN')} ₫`
                                    ];
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(51, 65, 85, 0.4)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 11 },
                                callback: (v) => {
                                    if (v >= 1000000) return (v / 1000000).toFixed(0) + ' Tr';
                                    return v.toLocaleString('vi-VN');
                                }
                            }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#f8fafc', font: { size: 11, weight: '500' } }
                        }
                    }
                }
            });
        }

        // Render Biểu đồ Doughnut Cơ Cấu Trạng Thái
        function renderHwStatusChart(statusMap, totalOrders, totalAmount) {
            const ctx = document.getElementById('hwStatusChart');
            const legendEl = document.getElementById('hwStatusLegend');
            if (!ctx) return;

            if (hwStatusChartInstance) {
                hwStatusChartInstance.destroy();
            }

            const STATUS_PALETTE = {
                'Thành công': { color: '#10b981', bg: 'rgba(16, 185, 129, 0.85)' },
                'Bán hàng': { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.85)' },
                'KH chuyển nhượng': { color: '#a855f7', bg: 'rgba(168, 85, 247, 0.85)' },
                'Đã chuyển nhượng': { color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.85)' },
                'Thất bại': { color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.85)' },
                'Chờ Xét Duyệt': { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.85)' },
                'Hợp đồng thanh lý': { color: '#64748b', bg: 'rgba(100, 116, 139, 0.85)' },
                'KH đang thanh toán': { color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.85)' }
            };

            const entries = Object.entries(statusMap).sort((a, b) => b[1].count - a[1].count);
            const labels = entries.map(e => e[0]);
            const counts = entries.map(e => e[1].count);
            const amounts = entries.map(e => e[1].amount);
            const colors = labels.map(l => STATUS_PALETTE[l]?.color || '#94a3b8');
            const bgColors = labels.map(l => STATUS_PALETTE[l]?.bg || 'rgba(148, 163, 184, 0.85)');

            hwStatusChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: bgColors,
                        borderColor: '#0f172a',
                        borderWidth: 2,
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            borderColor: 'rgba(51, 65, 85, 0.8)',
                            borderWidth: 1,
                            padding: 10,
                            callbacks: {
                                label: (item) => {
                                    const idx = item.dataIndex;
                                    const cnt = counts[idx];
                                    const amt = amounts[idx];
                                    const pct = totalOrders > 0 ? (cnt * 100 / totalOrders).toFixed(1) : 0;
                                    return [
                                        `📦 Số lượng: ${cnt} đơn (${pct}%)`,
                                        `💰 Thành tiền: ${amt.toLocaleString('vi-VN')} ₫`
                                    ];
                                }
                            }
                        }
                    }
                }
            });

            // Render custom status legend
            if (legendEl) {
                legendEl.innerHTML = entries.map(e => {
                    const st = e[0];
                    const d = e[1];
                    const pct = totalOrders > 0 ? (d.count * 100 / totalOrders).toFixed(1) : 0;
                    const c = STATUS_PALETTE[st]?.color || '#94a3b8';
                    return `
                        <div class="flex items-center justify-between p-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-[11px]">
                            <span class="flex items-center gap-1.5 truncate max-w-[120px]">
                                <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${c}"></span>
                                <span class="truncate text-slate-300" title="${st}">${st}</span>
                            </span>
                            <span class="font-bold text-white">${d.count} <span class="text-slate-400 font-normal">(${pct}%)</span></span>
                        </div>
                    `;
                }).join('');
            }
        }

        // Render Bảng 1: Bảng Nhân Sự
        function renderHwStaffTable(staffList, totalOrders, succOrders, succAmount, totalAmount) {
            const tbody = document.getElementById('hwStaffTableBody');
            const tfoot = document.getElementById('hwStaffTableFoot');
            const badge = document.getElementById('hwStaffCountBadge');
            if (badge) badge.innerText = staffList.length;

            if (tbody) {
                tbody.innerHTML = staffList.map((s, idx) => {
                    let rankBadge = `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-800 text-slate-400 text-[11px] font-bold">${idx + 1}</span>`;
                    if (idx === 0) rankBadge = `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-400 text-slate-900 text-[11px] font-bold shadow-md shadow-amber-400/30">1</span>`;
                    else if (idx === 1) rankBadge = `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-300 text-slate-900 text-[11px] font-bold">2</span>`;
                    else if (idx === 2) rankBadge = `<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-600 text-white text-[11px] font-bold">3</span>`;

                    const rateColor = s.rate >= 80 ? 'text-emerald-400' : (s.rate >= 60 ? 'text-blue-400' : (s.rate >= 40 ? 'text-amber-400' : 'text-rose-400'));
                    const rateBarBg = s.rate >= 80 ? 'bg-emerald-500' : (s.rate >= 60 ? 'bg-blue-500' : (s.rate >= 40 ? 'bg-amber-500' : 'bg-rose-500'));

                    return `
                        <tr class="hover:bg-slate-800/40 transition">
                            <td class="py-3 px-3 text-center">${rankBadge}</td>
                            <td class="py-3 px-4 font-semibold text-white max-w-[260px] truncate" title="${s.name}">${s.name}</td>
                            <td class="py-3 px-3 text-center text-slate-300 font-bold">${s.total_orders}</td>
                            <td class="py-3 px-3 text-center text-emerald-400 font-bold bg-emerald-500/5">${s.succ_orders}</td>
                            <td class="py-3 px-3 text-center text-blue-400">${s.sell_orders || 0}</td>
                            <td class="py-3 px-3 text-center text-purple-400">${s.transfer_orders || 0}</td>
                            <td class="py-3 px-3 text-center text-rose-400">${s.fail_orders || 0}</td>
                            <td class="py-3 px-3 text-center text-slate-400">${s.other_orders || 0}</td>
                            <td class="py-3 px-3 text-center">
                                <div class="flex items-center justify-center gap-2">
                                    <span class="font-bold ${rateColor}">${s.rate.toFixed(1)}%</span>
                                    <div class="w-12 bg-slate-700/80 rounded-full h-1.5 overflow-hidden">
                                        <div class="h-full ${rateBarBg}" style="width: ${Math.min(100, s.rate)}%"></div>
                                    </div>
                                </div>
                            </td>
                            <td class="py-3 px-4 text-right font-black text-emerald-300 bg-emerald-500/10 tracking-tight text-sm">${s.succ_amount.toLocaleString('vi-VN')} ₫</td>
                            <td class="py-3 px-4 text-right text-slate-300 font-semibold">${s.total_amount.toLocaleString('vi-VN')} ₫</td>
                        </tr>
                    `;
                }).join('');
            }

            if (tfoot) {
                const succRateTotal = totalOrders > 0 ? (succOrders * 100 / totalOrders).toFixed(1) : 0;
                tfoot.innerHTML = `
                    <tr>
                        <td class="py-3 px-3 text-center uppercase tracking-wider text-xs">Σ</td>
                        <td class="py-3 px-4 text-white uppercase tracking-wider font-extrabold text-xs">TỔNG CỘNG</td>
                        <td class="py-3 px-3 text-center text-white text-sm font-black">${totalOrders.toLocaleString()}</td>
                        <td class="py-3 px-3 text-center text-emerald-400 text-sm font-black">${succOrders.toLocaleString()}</td>
                        <td class="py-3 px-3 text-center text-blue-400 font-bold">${staffList.reduce((acc, s) => acc + (s.sell_orders || 0), 0)}</td>
                        <td class="py-3 px-3 text-center text-purple-400 font-bold">${staffList.reduce((acc, s) => acc + (s.transfer_orders || 0), 0)}</td>
                        <td class="py-3 px-3 text-center text-rose-400 font-bold">${staffList.reduce((acc, s) => acc + (s.fail_orders || 0), 0)}</td>
                        <td class="py-3 px-3 text-center text-slate-400 font-bold">${staffList.reduce((acc, s) => acc + (s.other_orders || 0), 0)}</td>
                        <td class="py-3 px-3 text-center text-amber-300 font-black text-sm">${succRateTotal}%</td>
                        <td class="py-3 px-4 text-right text-emerald-300 text-base font-black tracking-tight">${succAmount.toLocaleString('vi-VN')} ₫</td>
                        <td class="py-3 px-4 text-right text-white text-base font-black tracking-tight">${totalAmount.toLocaleString('vi-VN')} ₫</td>
                    </tr>
                `;
            }
        }

        // Render Bảng 2: Danh Sách Đơn Hàng Chi Tiết
        function renderHardwareOrdersTable() {
            const tbody = document.getElementById('hwOrdersTableBody');
            const countEl = document.getElementById('hwFilteredOrdersCount');
            const pageNumEl = document.getElementById('hwPageNum');
            const totalPagesEl = document.getElementById('hwTotalPages');
            const prevBtn = document.getElementById('hwPrevPageBtn');
            const nextBtn = document.getElementById('hwNextPageBtn');

            const total = lastFilteredHwRecords.length;
            if (countEl) countEl.innerText = total.toLocaleString();

            const totalPages = Math.max(1, Math.ceil(total / hwPageSize));
            if (hwCurrentPage > totalPages) hwCurrentPage = totalPages;
            if (hwCurrentPage < 1) hwCurrentPage = 1;

            if (pageNumEl) pageNumEl.innerText = hwCurrentPage;
            if (totalPagesEl) totalPagesEl.innerText = totalPages;

            if (prevBtn) prevBtn.disabled = hwCurrentPage <= 1;
            if (nextBtn) nextBtn.disabled = hwCurrentPage >= totalPages;

            const startIdx = (hwCurrentPage - 1) * hwPageSize;
            const pageItems = lastFilteredHwRecords.slice(startIdx, startIdx + hwPageSize);

            const STATUS_BADGES = {
                'Thành công': 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
                'Bán hàng': 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
                'KH chuyển nhượng': 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
                'Đã chuyển nhượng': 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold',
                'Thất bại': 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
                'Chờ Xét Duyệt': 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
                'Hợp đồng thanh lý': 'bg-slate-700 text-slate-300 border border-slate-600',
                'KH đang thanh toán': 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
            };

            if (tbody) {
                if (pageItems.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-500 italic">Không tìm thấy đơn hàng nào phù hợp bộ lọc.</td></tr>`;
                    return;
                }

                tbody.innerHTML = pageItems.map((r, i) => {
                    const stBadge = STATUS_BADGES[r.status] || 'bg-slate-800 text-slate-300 border border-slate-700';
                    const isSucc = (r.status === 'Thành công' || r.status === 'Đã chuyển nhượng');
                    const amtClass = isSucc ? 'text-emerald-400 font-bold' : 'text-slate-300';

                    return `
                        <tr class="hover:bg-slate-800/40 transition">
                            <td class="py-2.5 px-3 text-center text-slate-400">${startIdx + i + 1}</td>
                            <td class="py-2.5 px-3 font-mono font-semibold text-sky-400">${r.contract_no || '---'}</td>
                            <td class="py-2.5 px-3 font-mono text-slate-400">${r.retailer_id || '---'}</td>
                            <td class="py-2.5 px-4 font-medium text-white max-w-[200px] truncate" title="${r.store_name}">${r.store_name || '---'}</td>
                            <td class="py-2.5 px-4 text-right ${amtClass}">${r.amount.toLocaleString('vi-VN')} ₫</td>
                            <td class="py-2.5 px-3 text-center">
                                <span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${stBadge}">${r.status}</span>
                            </td>
                            <td class="py-2.5 px-4 text-slate-300 max-w-[220px] truncate" title="${r.staff}">${r.staff}</td>
                            <td class="py-2.5 px-3 text-slate-400 text-[11px] whitespace-nowrap">${r.created_at || '---'}</td>
                        </tr>
                    `;
                }).join('');
            }
        }

