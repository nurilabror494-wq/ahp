/**
 * SPK AHP Application Client Script
 * Handles Charts, Dynamic Comparison Matrix Feedback, and Helpers
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Inisialisasi Tooltip Bootstrap jika ada
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // 2. Pairwise Comparison live feedback
    const comparisonCards = document.querySelectorAll(".comparison-pair-card");
    comparisonCards.forEach(card => {
        const favSelect = card.querySelector(".fav-selector");
        const valSelect = card.querySelector(".val-selector");
        const descText = card.querySelector(".pair-desc-text");

        if (favSelect && valSelect && descText) {
            const updateDescription = () => {
                const fav = favSelect.value;
                const val = parseInt(valSelect.value, 10);
                const name1 = card.getAttribute("data-name1") || "Elemen 1";
                const name2 = card.getAttribute("data-name2") || "Elemen 2";

                const saatyTexts = {
                    1: "Sama penting dengan",
                    2: "Mendekati sedikit lebih penting daripada",
                    3: "Sedikit lebih penting daripada",
                    4: "Mendekati lebih penting daripada",
                    5: "Lebih penting (kuat) daripada",
                    6: "Mendekati sangat penting daripada",
                    7: "Sangat penting daripada",
                    8: "Mendekati mutlak lebih penting daripada",
                    9: "Mutlak lebih penting daripada"
                };

                const intensity = saatyTexts[val] || "Sama penting";
                if (val === 1) {
                    descText.innerHTML = `<span class="badge bg-secondary">Skala 1</span> <strong>${name1}</strong> sama pentingnya dengan <strong>${name2}</strong>`;
                } else if (fav === "c1" || fav === "a1") {
                    descText.innerHTML = `<span class="badge bg-primary">Skala ${val}</span> <strong>${name1}</strong> <em>${intensity}</em> <strong>${name2}</strong>`;
                } else {
                    descText.innerHTML = `<span class="badge bg-info text-dark">Skala ${val}</span> <strong>${name2}</strong> <em>${intensity}</em> <strong>${name1}</strong>`;
                }
            };

            favSelect.addEventListener("change", updateDescription);
            valSelect.addEventListener("change", updateDescription);
            updateDescription();
        }
    });
});

/**
 * Render Chart Bobot Prioritas Kriteria (Donut & Bar)
 */
function renderCriteriaChart(canvasId, labels, dataValues) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataValues,
                backgroundColor: [
                    '#1d4ed8', // Solid Royal Blue
                    '#059669', // Solid Emerald
                    '#d97706', // Solid Amber
                    '#7c3aed', // Solid Purple
                    '#0d9488', // Solid Teal
                    '#0284c7', // Solid Sky
                    '#dc2626'  // Solid Crimson
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 10,
                        padding: 10,
                        font: { size: 11, weight: '500' }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return ` ${context.label}: ${context.raw}%`;
                        }
                    }
                }
            },
            cutout: '70%'
        }
    });
}

/**
 * Render Chart Ranking Alternatif (Bar Chart)
 */
function renderRankingsChart(canvasId, labels, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;

    // Warna solid: Peringkat 1 hijau solid emerald, sisanya biru solid
    const bgColors = scores.map((_, i) => i === 0 ? '#059669' : '#1d4ed8');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Skor Akhir AHP',
                data: scores,
                backgroundColor: bgColors,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: Math.max(...scores, 0.5) * 1.15,
                    ticks: {
                        callback: function (val) {
                            return (val * 100).toFixed(0) + '%';
                        }
                    },
                    grid: {
                        color: '#f1f5f9'
                    }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const val = context.raw;
                            return `Skor: ${val.toFixed(4)} (${(val * 100).toFixed(2)}%)`;
                        }
                    }
                }
            }
        }
    });
}
