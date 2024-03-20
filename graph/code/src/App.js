import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Colors,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import APIBackend from './RestAPI'

import * as dayjs from 'dayjs'
import * as weekOfYear from 'dayjs/plugin/weekOfYear';
import * as advancedFormat from 'dayjs/plugin/advancedFormat';

import './app.css'

dayjs.extend(weekOfYear)
dayjs.extend(advancedFormat)

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Colors,
  Legend
);

function set_alpha(colour, alpha) {
  let out = colour
  // Regex to extract the numbers from a string like this "rgba(255,159,64,0.5)"
  let rgba = colour.match(/^rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+[\.]?\d*)\s*\)$/i);
  if (rgba) {
    out = "rgba(" + rgba[1] + "," + rgba[2] + "," + rgba[3] + "," + alpha + ")";
  }
  else {
    let rgb = colour.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
    if (rgb) {
      out = "rgba(" + rgb[1] + "," + rgb[2] + "," + rgb[3] + "," + alpha + ")";
    }
  }
  return out
}

//from example here: https://github.com/chartjs/Chart.js/blob/master/docs/samples/legend/events.md
function handleHover(evt, item, legend) {
  legend.chart.data.datasets.forEach((dataset, index) => {
    dataset.backgroundColor = index === item.datasetIndex ? dataset.backgroundColor : set_alpha(dataset.backgroundColor, 0.2);
    dataset.borderColor = index === item.datasetIndex ? dataset.borderColor : set_alpha(dataset.borderColor, 0.1);
  });
  legend.chart.update();
}

function handleLeave(evt, item, legend) {
  legend.chart.data.datasets.forEach((dataset) => {
    dataset.backgroundColor = set_alpha(dataset.backgroundColor, 0.5);
    dataset.borderColor = set_alpha(dataset.borderColor, 1.0);
  });
  legend.chart.update();
}


export const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      onHover: handleHover,
      onLeave: handleLeave
    },
    // title: {
    //   display: true,
    //   text: 'Chart.js Line Chart',
    // },
  },
  interaction: {
    axis: "x",
    mode: "nearest",
    intersect: false,
  }
};

function App() {
  let [loaded, setLoaded] = React.useState(false)
  let [pending, setPending] = React.useState(false)
  let [error, setError] = React.useState(null)
  let [config, setConfig] = React.useState(undefined)

  React.useEffect(() => {
    const do_load = async () => {
      setPending(true)
      APIBackend.api_get('http://' + document.location.host + '/config/config.json').then((response) => {
        if (response.status === 200) {
          console.log("config ", response.payload)
          setConfig(response.payload)
          setLoaded(true)
        } else {
          console.log("ERROR LOADING CONFIG")
          setError("ERROR: Unable to load configuration!")
        }
      }).catch((err) => {
        console.error(err.message);
        setError("ERROR: Unable to load configuration!")
      })
    }

    if (!loaded && !pending) {
      do_load()
    }
  }, [loaded, pending])

  if (!loaded) {
    return error ? error : "Loading..."
  }

  return (
    <Graph config={config} />
  );
}

function Graph({ config }) {
  let [loaded, setLoaded] = React.useState(false)
  let [pending, setPending] = React.useState(false)
  let [error, setError] = React.useState(null)

  let [data, setData] = React.useState({})
  let [type, setType] = React.useState("line")

  React.useEffect(() => {
    const do_load = async () => {
      setPending(true)

      let params = new URLSearchParams(window.location.search);
      setType(params.get("graph"))

      let url = (config.source.host ? config.source.host : window.location.hostname) + (config.source.port ? ":" + config.source.port : "")
      let path = window.location.pathname
      APIBackend.api_get('http://' + url + path + "?" + params.toString()).then((response) => {
        if (response.status === 200) {
          console.log("payload", response.payload)
          setData(response.payload)
          setLoaded(true)
        } else {
          console.log("ERROR LOADING DATA")
          setError("ERROR: Unable to load data!")
        }
      }).catch((err) => {
        console.error(err.message);
        setError("ERROR: Unable to load data!")
      })
    }

    if (!loaded && !pending) {
      do_load()
    }
  }, [config, loaded, pending])

  if (!loaded) {
    return error ? error : "Loading..."
  }
  if (data?.buckets?.length == 0) {
    return <h1>No data to display</h1>
  }

  let graph_data = {
    labels: data.buckets,
    datasets: Object.keys(data.series).map(series_key => ({
      label: series_key,
      data: data.series[series_key],
      borderWidth: 1
    }))
  };

  console.log(type)
  return (
    <div id="frame">
      {type === "line" ?
        <Line options={options} data={graph_data} />
        : <Bar options={options} data={graph_data} />
      }
    </div>
  )
}


export default App;

