"use strict";

if (module.hot) {
  module.hot.accept();
}

import Chart from "chart.js";

const timeFormat = "MM/DD/YYYY HH:mm";

window.makeChart = (labels, values) => {
    const color = Chart.helpers.color;
    const config = {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Contributions",
            backgroundColor: color("red")
              .alpha(0.5)
              .rgbString(),
            borderColor: "red",
            fill: false,
            data: values
          }
        ]
      },
      options: {
        scales: {
          xAxes: [
            {
              type: "time",
              time: {
                format: timeFormat,
                //round: 'day'
                tooltipFormat: "ll HH:mm"
              },
              scaleLabel: {
                display: true,
                labelString: "Date"
              }
            }
          ],
          yAxes: [
            {
              scaleLabel: {
                display: true,
                labelString: "Count"
              },
              ticks: {
                beginAtZero: true
              }
            }
          ]
        }
      }
    };

    var ctx = document.getElementById("canvas").getContext("2d");
    new Chart(ctx, config);
}
