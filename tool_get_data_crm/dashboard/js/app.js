// =============================================================================
// KIOTVIET CRM ANALYTICS - APP CORE (app.js)
// Quản lý điều hướng Module, Thanh tiến trình, Trạng thái đồng bộ Live API
// =============================================================================

// Cấu hình Endpoint Google Apps Script Web App
const ENDPOINT_API_URL = "https://script.google.com/macros/s/AKfycbzXWcRdOfuuKhAJY6j1MmDcwhOPqq4jpPIDCgp66M9-0LC2FQTWsn9Wcnk97hXTH3swLA/exec";

// Module đang chọn: 'impact' | 'hardware' | 'pctq'
let currentModule = 'impact';

/**
 * Cập nhật thanh tiến độ tải & nhãn trạng thái đồng bộ
 */
function updateLoadingProgress(percent, statusText, isError = false, isDone = false) {
    const topBar = document.getElementById('topProgressBar');
    const badge = document.getElementById('syncBadge');
    const dot = document.getElementById('syncDot');
    const text = document.getElementById('syncBadgeText');
    const track = document.getElementById('syncProgressTrack');
    const bar = document.getElementById('syncProgressBar');

    if (topBar) {
        if (isDone) {
            topBar.style.width = '100%';
            topBar.style.opacity = '1';
            setTimeout(() => {
                topBar.style.opacity = '0';
                setTimeout(() => { topBar.style.width = '0%'; }, 300);
            }, 600);
        } else if (isError) {
            topBar.style.opacity = '0';
            topBar.style.width = '0%';
        } else {
            topBar.style.opacity = '1';
            topBar.style.width = `${percent}%`;
        }
    }

    if (badge && text) {
        text.innerText = statusText;
        if (isDone) {
            badge.className = "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 transition-all duration-300 shadow-sm";
            if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-400";
            if (track) track.classList.add('hidden');
        } else if (isError) {
            badge.className = "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 transition-all duration-300 shadow-sm";
            if (dot) dot.className = "w-2 h-2 rounded-full bg-amber-400";
            if (track) track.classList.add('hidden');
        } else {
            badge.className = "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 transition-all duration-300 shadow-sm";
            if (dot) dot.className = "w-2 h-2 rounded-full bg-blue-400 animate-ping";
            if (track) track.classList.remove('hidden');
            if (bar) bar.style.width = `${percent}%`;
        }
    }
}

/**
 * Chuyển đổi giữa 3 Tab Báo Cáo
 */
function switchModule(moduleName) {
    currentModule = moduleName;
    const impactSec = document.getElementById('impactModuleSection');
    const hwSec = document.getElementById('hardwareModuleSection');
    const pctqSec = document.getElementById('pctqModuleSection');
    const navImpact = document.getElementById('navImpactBtn');
    const navHw = document.getElementById('navHardwareBtn');
    const navPCTQ = document.getElementById('navPCTQBtn');
    const quickText = document.getElementById('moduleQuickStatsText');

    if (moduleName === 'pctq') {
        if (impactSec) impactSec.classList.add('hidden');
        if (hwSec) hwSec.classList.add('hidden');
        if (pctqSec) pctqSec.classList.remove('hidden');

        if (navPCTQ) navPCTQ.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg transition";
        if (navHw) navHw.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";
        if (navImpact) navImpact.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";

        if (quickText) quickText.innerHTML = `Đang xem: <strong class="text-violet-400">Phần Cứng Toàn Quốc</strong> (Sheet: phancungtoanquoc)`;

        if (typeof populatePCTQFilters === 'function') populatePCTQFilters();
        if (typeof renderPCTQDashboard === 'function') renderPCTQDashboard();
        if (typeof pctqLoaded !== 'undefined' && !pctqLoaded) {
            pctqLoaded = true;
            if (typeof fetchPCTQLive === 'function') fetchPCTQLive();
        }
    } else if (moduleName === 'hardware') {
        if (impactSec) impactSec.classList.add('hidden');
        if (pctqSec) pctqSec.classList.add('hidden');
        if (hwSec) hwSec.classList.remove('hidden');

        if (navPCTQ) navPCTQ.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";
        if (navHw) navHw.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg transition";
        if (navImpact) navImpact.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";

        if (quickText) quickText.innerHTML = `Đang xem: <strong class="text-emerald-400">Doanh thu Phần Cứng</strong> (Tab: <span class="text-teal-300 font-semibold">phancung</span> • Cột A:J)`;

        if (typeof populateHardwareFilterDropdowns === 'function') populateHardwareFilterDropdowns();
        if (typeof renderHardwareDashboard === 'function') renderHardwareDashboard();
        if (typeof isHwFetched !== 'undefined' && !isHwFetched) {
            if (typeof fetchHardwareLive === 'function') fetchHardwareLive();
        }
    } else {
        if (hwSec) hwSec.classList.add('hidden');
        if (pctqSec) pctqSec.classList.add('hidden');
        if (impactSec) impactSec.classList.remove('hidden');

        if (navImpact) navImpact.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg transition";
        if (navHw) navHw.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";
        if (navPCTQ) navPCTQ.className = "flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 md:px-5 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition";

        if (quickText) quickText.innerHTML = `Đang xem: Báo cáo tỷ lệ Impact (Sheet: DATA ➔ tudaunam)`;

        if (typeof chartInstance !== 'undefined' && chartInstance) chartInstance.resize();
    }
}

/**
 * Nút 'Làm mới số liệu': Tự động điều hướng làm mới theo tab hiện tại
 */
async function fetchLiveOrReload() {
    const icon = document.getElementById('refreshIcon');
    if (icon) icon.classList.add('fa-spin');

    if (currentModule === 'pctq') {
        if (typeof fetchPCTQLive === 'function') await fetchPCTQLive(true);
    } else if (currentModule === 'hardware') {
        if (typeof fetchHardwareLive === 'function') await fetchHardwareLive(true);
    } else {
        if (typeof fetchImpactLiveOrReload === 'function') await fetchImpactLiveOrReload();
    }

    if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 600);
}

// Khởi chạy khi tài liệu HTML sẵn sàng
window.addEventListener('DOMContentLoaded', () => {
    // Khởi tạo tab Impact mặc định
    if (typeof renderMonthPills === 'function') renderMonthPills();
    if (typeof applyFilters === 'function') applyFilters();
    if (typeof fetchImpactLiveOrReload === 'function') fetchImpactLiveOrReload();

    // Điều hướng theo URL query param hoặc hash (#hardware, #pctq)
    const hash = window.location.hash.toLowerCase();
    const search = window.location.search.toLowerCase();
    if (hash === '#pctq' || search.includes('tab=pctq')) {
        switchModule('pctq');
    } else if (hash === '#hardware' || search.includes('tab=hardware')) {
        switchModule('hardware');
    }
});
