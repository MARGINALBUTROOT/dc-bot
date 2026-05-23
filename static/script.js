// Sayfayı yönet
const sections = document.querySelectorAll('.section');
const menuItems = document.querySelectorAll('.menu-item');

menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const sectionName = item.dataset.section;
        
        // Menüyü güncelle
        menuItems.forEach(m => m.classList.remove('active'));
        item.classList.add('active');
        
        // Seciton'u göster
        sections.forEach(s => s.classList.remove('active'));
        document.getElementById(`${sectionName}-section`).classList.add('active');
        
        // Header'ı güncelle
        document.querySelector('.header h1').textContent = 
            sectionName === 'dashboard' ? 'Dashboard' :
            sectionName === 'logs' ? 'Moderasyon Logları' :
            sectionName === 'stats' ? 'İstatistikler' :
            'Ayarlar';
    });
});

// API çağrıları
let refreshInterval;

async function loadData() {
    try {
        // Status
        const statusRes = await fetch('/api/status');
        const statusData = await statusRes.json();
        updateStatus(statusData);
        
        // Logs
        const logsRes = await fetch('/api/logs');
        const logsData = await logsRes.json();
        updateLogs(logsData.logs);
        
        // Stats
        const statsRes = await fetch('/api/stats');
        const statsData = await statsRes.json();
        updateStats(statsData);
    } catch (error) {
        console.error('Veri yüklemede hata:', error);
    }
}

function updateStatus(data) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    if (data.status === 'online') {
        indicator.classList.add('online');
        statusText.textContent = '🟢 Çevrimiçi';
    } else {
        indicator.classList.remove('online');
        statusText.textContent = '🔴 Çevrimdışı';
    }
    
    // İstatistikler
    document.getElementById('stat-bans').textContent = data.stats.total_bans;
    document.getElementById('stat-kicks').textContent = data.stats.total_kicks;
    document.getElementById('stat-warns').textContent = data.stats.total_warns;
    document.getElementById('stat-mutes').textContent = data.stats.total_mutes;
}

function updateLogs(logs) {
    const tbody = document.getElementById('recent-tbody');
    const logsTableBody = document.getElementById('logs-tbody');
    
    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">Henüz log yok</td></tr>';
        logsTableBody.innerHTML = '<tr><td colspan="5">Henüz log yok</td></tr>';
        return;
    }
    
    // Recent logs (dashboard'da ilk 5)
    tbody.innerHTML = logs.slice(0, 5).map(log => `
        <tr>
            <td><span class="badge">${getActionBadge(log.action)}</span></td>
            <td>${log.moderator}</td>
            <td>${log.target}</td>
            <td>${log.reason}</td>
        </tr>
    `).join('');
    
    // All logs (logs page)
    logsTableBody.innerHTML = logs.map(log => `
        <tr>
            <td><span class="badge">${getActionBadge(log.action)}</span></td>
            <td>${log.moderator}</td>
            <td>${log.target}</td>
            <td>${log.reason}</td>
            <td>${log.guild_id}</td>
        </tr>
    `).join('');
}

function updateStats(stats) {
    const actionStatsDiv = document.getElementById('action-stats');
    const modStatsDiv = document.getElementById('mod-stats');
    
    // İşlem istatistikleri
    actionStatsDiv.innerHTML = Object.entries(stats.by_action).map(([action, count]) => `
        <div class="stat-item">
            <span class="stat-name">${action}</span>
            <span class="stat-value">${count}</span>
        </div>
    `).join('');
    
    // Moderatör istatistikleri
    modStatsDiv.innerHTML = Object.entries(stats.by_moderator).map(([mod, count]) => `
        <div class="stat-item">
            <span class="stat-name">${mod}</span>
            <span class="stat-value">${count}</span>
        </div>
    `).join('');
}

function getActionBadge(action) {
    const badges = {
        'BAN': '🚫 Yasak',
        'KICK': '👢 Atıldı',
        'WARN': '⚠️ Uyarı',
        'MUTE': '🔇 Sustur',
        'UNMUTE': '🔊 Açıldı',
        'PURGE': '🗑️ Silme',
        'LOCK': '🔒 Kilitle',
        'UNLOCK': '🔓 Aç'
    };
    return badges[action] || action;
}

// Filtreler
document.getElementById('filter-action').addEventListener('change', async (e) => {
    const action = e.target.value;
    try {
        const res = await fetch(`/api/logs/filter?action=${action}`);
        const data = await res.json();
        const logsTableBody = document.getElementById('logs-tbody');
        logsTableBody.innerHTML = data.logs.map(log => `
            <tr>
                <td><span class="badge">${getActionBadge(log.action)}</span></td>
                <td>${log.moderator}</td>
                <td>${log.target}</td>
                <td>${log.reason}</td>
                <td>${log.guild_id}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Filtreleme hatası:', error);
    }
});

document.getElementById('search-user').addEventListener('input', async (e) => {
    const user = e.target.value;
    if (!user) {
        loadData();
        return;
    }
    
    try {
        const res = await fetch(`/api/logs/user/${user}`);
        const data = await res.json();
        const logsTableBody = document.getElementById('logs-tbody');
        logsTableBody.innerHTML = data.logs.map(log => `
            <tr>
                <td><span class="badge">${getActionBadge(log.action)}</span></td>
                <td>${log.moderator}</td>
                <td>${log.target}</td>
                <td>${log.reason}</td>
                <td>${log.guild_id}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Arama hatası:', error);
    }
});

// Bot kontrolleri
document.getElementById('refresh-btn').addEventListener('click', loadData);

document.getElementById('restart-btn').addEventListener('click', async () => {
    if (confirm('Bot'u gerçekten yeniden başlatmak istiyor musun?')) {
        try {
            const res = await fetch('/api/bot/restart', { method: 'POST' });
            const data = await res.json();
            alert('Bot yeniden başlatılıyor...');
        } catch (error) {
            alert('Hata: ' + error.message);
        }
    }
});

document.getElementById('stop-btn').addEventListener('click', async () => {
    if (confirm('Bot'u gerçekten durdurmak istiyor musun?')) {
        try {
            const res = await fetch('/api/bot/stop', { method: 'POST' });
            const data = await res.json();
            alert('Bot durduruldu');
            loadData();
        } catch (error) {
            alert('Hata: ' + error.message);
        }
    }
});

// Badge stili
const style = document.createElement('style');
style.textContent = `
    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        background: #ecf0f1;
        color: #2c3e50;
    }
`;
document.head.appendChild(style);

// İlk yükleme
loadData();

// Otomatik yenile (10 saniye)
refreshInterval = setInterval(loadData, 10000);
