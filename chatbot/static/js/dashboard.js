
// Generate sample dates for the past 30 days
const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().split('T')[0];
});

// Mock data for each clinical metric
const glucoseData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 50) + 90); // 90-140
const cholesterolData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 50) + 150); // 150-200
const systolicData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 20) + 110); // 110-130
const diastolicData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 15) + 70); // 70-85

const ctx = document.getElementById('clinicalChart').getContext('2d');

const clinicalChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: days,
        datasets: [
            {
                label: 'Glucose Level',
                data: glucoseData,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.3
            },
            {
                label: 'Cholesterol Total',
                data: cholesterolData,
                borderColor: 'rgba(255, 159, 64, 1)',
                backgroundColor: 'rgba(255, 159, 64, 0.1)',
                tension: 0.3
            },
            {
                label: 'Systolic BP',
                data: systolicData,
                borderColor: 'rgba(153, 102, 255, 1)',
                backgroundColor: 'rgba(153, 102, 255, 0.1)',
                tension: 0.3
            },
            {
                label: 'Diastolic BP',
                data: diastolicData,
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.3
            }
        ]
    },
    options: {
        responsive: true,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        stacked: false,
        plugins: {
            title: {
                display: false,
                text: 'Clinical Data Trends'
            }
        },
        scales: {
            y: {
                beginAtZero: false,
                title: {
                    display: true,
                    text: 'Measurement Units'
                }
            },
            x: {
                title: {
                    display: true,
                    text: 'Date'
                }
            }
        }
    }
});
