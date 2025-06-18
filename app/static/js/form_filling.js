document.addEventListener('DOMContentLoaded', function() {
    

    function nextStep() { 
        setActiveStep(activeStep + 1); 
    }

    function prevStep() { 
        setActiveStep(activeStep - 1); 
    }

    function extractForm() { 
        alert(`Extracting form from URL: ${formUrl}`); 
    }

    function updateSubmissionCount(count) { 
        submissionCount = parseInt(count); 
    }

    function updateSubmissionRate(rate) { 
        submissionRate = parseInt(rate); 
    }

    function updateThreads(t) { 
        threads = parseInt(t); 
    }

    function toggleAutomation() {
        alert(progress == 0 ? "Automation cancelled" : "Automation paused");
    }

    // Gán các hàm vào window để có thể gọi từ HTML
    window.setActiveStep = setActiveStep;
    window.updateFormUrl = updateFormUrl;
    window.nextStep = nextStep;
    window.prevStep = prevStep;
    window.extractForm = extractForm;
    window.updateSubmissionCount = updateSubmissionCount;
    window.updateSubmissionRate = updateSubmissionRate;
    window.updateThreads = updateThreads;
    window.toggleAutomation = toggleAutomation;

    // Khởi tạo biểu đồ nếu ở bước 4
    if (activeStep === 4 && typeof echarts !== 'undefined') {
        const textColor = darkMode ? 'white' : 'black';
        
        const cpuChart = echarts.init(document.getElementById('cpuChart'));
        cpuChart.setOption({
            title: { 
                text: 'CPU Usage', 
                left: 'center', 
                textStyle: { color: textColor } 
            },
            xAxis: { 
                type: 'category', 
                data: ['1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '10m'], 
                axisLabel: { color: textColor } 
            },
            yAxis: { 
                type: 'value', 
                max: 100, 
                axisLabel: { 
                    formatter: '{value}%', 
                    color: textColor 
                } 
            },
            series: [{ 
                data: [12, 24, 36, 42, 38, 25, 30, 35, 40, 45], 
                type: 'line', 
                smooth: true 
            }]
        });

        const memoryChart = echarts.init(document.getElementById('memoryChart'));
        memoryChart.setOption({
            title: { 
                text: 'Memory Usage', 
                left: 'center', 
                textStyle: { color: textColor } 
            },
            xAxis: { 
                type: 'category', 
                data: ['1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '10m'], 
                axisLabel: { color: textColor } 
            },
            yAxis: { 
                type: 'value', 
                max: 100, 
                axisLabel: { 
                    formatter: '{value}%', 
                    color: textColor 
                } 
            },
            series: [{ 
                data: [28, 32, 45, 50, 55, 60, 58, 62, 65, 68], 
                type: 'line', 
                smooth: true 
            }]
        });
    }
});