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

// Configuração específica para o gráfico de vibração
const vibrationChartOptions = {
    ...chartOptions,
    scales: {
        ...chartOptions.scales,
        y: {
            ...chartOptions.scales.y,
            min: 0,
            max: 9,
            ticks: {
                stepSize: 1
            }
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
            label: 'Magnitude (0-9)',
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
    options: vibrationChartOptions
});

// Elementos DOM
const statusBadge = document.getElementById('status-badge');
const lastUpdate = document.getElementById('last-update');
const currentTemperature = document.getElementById('current-temperature');
const currentHumidity = document.getElementById('current-humidity');
const currentVibration = document.getElementById('current-vibration');
const alertsContainer = document.getElementById('alerts-container');

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

// Função para extrair o valor correto com base no formato do objeto de dados
function extractSensorValue(item) {
    // Se item já for um número, retornar diretamente
    if (typeof item.value === 'number') {
        return item.value;
    }
    
    // Se for um objeto JSON em string, tentar converter
    if (typeof item.value === 'object') {
        // Para temperatura
        if (item.value.temperature !== undefined) {
            return item.value.temperature;
        }
        // Para umidade
        if (item.value.humidity !== undefined) {
            return item.value.humidity;
        }
        // Para vibração - diferentes formatos
        if (item.value.magnitude !== undefined) {
            return item.value.magnitude;
        }
        if (item.value.level !== undefined) {
            return item.value.level;
        }
        if (item.value.vibration_level !== undefined) {
            return item.value.vibration_level;
        }
        if (item.value.current_magnitude !== undefined) {
            return item.value.current_magnitude;
        }
    }
    
    // Caso não consiga extrair o valor, retornar o valor original
    return item.value;
}

// Função para atualizar os alertas na interface
function updateAlerts(alerts) {
    // Limpar container de alertas
    alertsContainer.innerHTML = '';
    
    // Se não houver alertas, não fazer nada
    if (!alerts || alerts.length === 0) return;
    
    // Ordenar alertas por nível (perigo primeiro)
    const sortedAlerts = [...alerts].sort((a, b) => {
        if (a.level === 'danger' && b.level !== 'danger') return -1;
        if (a.level !== 'danger' && b.level === 'danger') return 1;
        return 0;
    });
    
    // Criar e adicionar cada alerta
    sortedAlerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${alert.level} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        
        // Adicionar ícone apropriado
        let icon = '';
        if (alert.level === 'danger') {
            icon = '<i class="bi bi-exclamation-triangle-fill me-2"></i>';
        } else {
            icon = '<i class="bi bi-exclamation-circle-fill me-2"></i>';
        }
        
        alertDiv.innerHTML = `
            ${icon}
            <strong>${alert.message}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
        `;
        
        alertsContainer.appendChild(alertDiv);
    });
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
    
    // Atualizar alertas
    if (data.alerts) {
        updateAlerts(data.alerts);
    }
    
    // Atualizar temperatura
    if (data.temperature && data.temperature.length > 0) {
        const labels = data.temperature.map(item => item.time);
        const values = data.temperature.map(item => {
            return extractSensorValue(item);
        });
        
        temperatureChart.data.labels = labels;
        temperatureChart.data.datasets[0].data = values;
        temperatureChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentTemperature.textContent = lastValue !== undefined ? `${lastValue.toFixed(1)} °C` : '--';
        
        // Destacar valor se estiver acima do normal
        if (lastValue > 50) {
            currentTemperature.className = 'text-danger';
        } else if (lastValue > 40) {
            currentTemperature.className = 'text-warning';
        } else {
            currentTemperature.className = '';
        }
    }
    
    // Atualizar umidade
    if (data.humidity && data.humidity.length > 0) {
        const labels = data.humidity.map(item => item.time);
        const values = data.humidity.map(item => {
            return extractSensorValue(item);
        });
        
        humidityChart.data.labels = labels;
        humidityChart.data.datasets[0].data = values;
        humidityChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentHumidity.textContent = lastValue !== undefined ? `${lastValue.toFixed(1)} %` : '--';
        
        // Destacar valor se estiver acima do normal
        if (lastValue > 85) {
            currentHumidity.className = 'text-warning';
        } else {
            currentHumidity.className = '';
        }
    }
    
    // Atualizar vibração (agora chamado de magnitude)
    if (data.vibration && data.vibration.length > 0) {
        const labels = data.vibration.map(item => item.time);
        const values = data.vibration.map(item => item.value); // Os valores já estão remapeados no backend
        
        vibrationChart.data.labels = labels;
        vibrationChart.data.datasets[0].data = values;
        vibrationChart.update();
        
        // Atualizar valor atual
        const lastValue = values[values.length - 1];
        currentVibration.textContent = lastValue !== undefined ? `${lastValue.toFixed(1)}/9.0` : '--';
        
        // Destacar valor de acordo com o nível
        if (lastValue > 7) {
            currentVibration.className = 'text-danger';
        } else if (lastValue > 5) {
            currentVibration.className = 'text-warning';
        } else {
            currentVibration.className = '';
        }
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
    
    // Adicionar link para ícones Bootstrap
    const iconLink = document.createElement('link');
    iconLink.rel = 'stylesheet';
    iconLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css';
    document.head.appendChild(iconLink);
}); 