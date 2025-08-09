document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        events: fetchEvents,
        eventDidMount: function(info) {
            var color = info.event.extendedProps.color || '#3788d8';
            info.el.style.backgroundColor = hexToRgba(color, 0.2);
            info.el.style.borderLeft = '4px solid ' + color;
            info.el.style.color = '#fff';
        }
    });
    calendar.render();

    function fetchEvents(fetchInfo, successCallback, failureCallback) {
        fetch('/schedule', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        })
        .then(resp => resp.json())
        .then(data => {
            var events = (data.scheduled || []).map(function(item) {
                var start = item.date + 'T' + item.start_time;
                var end = item.date + 'T' + item.end_time;
                var color;
                if (item.priority === 'high') color = '#e74c3c';
                else if (item.priority === 'low') color = '#27ae60';
                else color = '#f1c40f';
                return {
                    title: item.title,
                    start: start,
                    end: end,
                    allDay: false,
                    extendedProps: { color: color }
                };
            });
            successCallback(events);
        })
        .catch(failureCallback);
    }

    function hexToRgba(hex, alpha) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }
});
