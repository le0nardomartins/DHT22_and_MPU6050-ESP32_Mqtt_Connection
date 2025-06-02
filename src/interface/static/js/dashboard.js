// Configurações dos gráficos
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
        duration: 800,
        easing: 'easeOutQuart'
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(0, 0, 0, 0.05)'
            }
        }
    },
    plugins: {
        legend: {
            display: false
        }
    }
};

// Inicializar gráficos vazios
const temperatureCtx = document.getElementById('temperature-chart').getContext('2d');
const temperatureChart = new Chart(temperatureCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Temperatura (°C)',
            data: [],
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: 'rgba(255, 99, 132, 1)',
            tension: 0.4,
            fill: true
        }]
    },
    options: chartOptions
});

const humidityCtx = document.getElementById('humidity-chart').getContext('2d');
const humidityChart = new Chart(humidityCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Umidade (%)',
            data: [],
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: 'rgba(54, 162, 235, 1)',
            tension: 0.4,
            fill: true
        }]
    },
    options: chartOptions
});

const vibrationCtx = document.getElementById('vibration-chart').getContext('2d');
const vibrationChart = new Chart(vibrationCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Vibração',
            data: [],
            borderColor: 'rgba(255, 206, 86, 1)',
            backgroundColor: 'rgba(255, 206, 86, 0.2)',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: 'rgba(255, 206, 86, 1)',
            tension: 0.4,
            fill: true
        }]
    },
    options: chartOptions
});

// Elementos DOM
const statusBadge = document.getElementById('status-badge');
const lastUpdate = document.getElementById('last-update');
const currentTemperature = document.getElementById('current-temperature');
const currentHumidity = document.getElementById('current-humidity');
const currentVibration = document.getElementById('current-vibration');

// Função para atualizar o status do dispositivo
function updateStatus(status) {
    statusBadge.textContent = status;
    
    if (status === 'online') {
        statusBadge.className = 'badge bg-success';
    } else if (status === 'offline') {
        statusBadge.className = 'badge bg-danger';
    } else {
        statusBadge.className = 'badge bg-secondary';
    }
}

// Função para atualizar os gráficos com novos dados
function updateCharts(data) {
    // Atualizar última atualização
    if (data.last_update) {
        lastUpdate.textContent = `Última atualização: ${data.last_update}`;
    }
    
    // Atualizar status
    if (data.status) {
        updateStatus(data.status);
    }
    
    // Atualizar temperatura
    if (data.temperature && data.temperature.length > 0) {
        const labels = data.temperature.map(item => item.time);
        const values = data.temperature.map(item => item.value);
        
        temperatureChart.data.labels = labels;
        temperatureChart.data.datasets[0].data = values;
        temperatureChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentTemperature.textContent = lastValue !== undefined ? `${lastValue.toFixed(1)} °C` : '--';
    }
    
    // Atualizar umidade
    if (data.humidity && data.humidity.length > 0) {
        const labels = data.humidity.map(item => item.time);
        const values = data.humidity.map(item => item.value);
        
        humidityChart.data.labels = labels;
        humidityChart.data.datasets[0].data = values;
        humidityChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentHumidity.textContent = lastValue !== undefined ? `${lastValue.toFixed(1)} %` : '--';
    }
    
    // Atualizar vibração
    if (data.vibration && data.vibration.length > 0) {
        const labels = data.vibration.map(item => item.time);
        const values = data.vibration.map(item => item.value);
        
        vibrationChart.data.labels = labels;
        vibrationChart.data.datasets[0].data = values;
        vibrationChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentVibration.textContent = lastValue !== undefined ? lastValue.toFixed(2) : '--';
    }
}

// Função para buscar dados do servidor
function fetchData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            updateCharts(data);
        })
        .catch(error => {
            console.error('Erro ao buscar dados:', error);
        });
}

// Buscar dados iniciais e configurar atualização periódica
document.addEventListener('DOMContentLoaded', () => {
    // Buscar dados imediatamente
    fetchData();
    
    // Configurar atualização a cada 5 segundos
    setInterval(fetchData, 5000);
}); 