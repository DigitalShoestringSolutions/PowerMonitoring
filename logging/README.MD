# Viewing Logs
## Set up the Connection
1. Open Grafana
1. Go to Connections and add a new `Loki` data source
1. Set the `URL` to `http://loki.docker.local:3100`
1. Click `Save & test`

> If grafana is running on a different device use `http://<IP address of solution>:3100`

## Find the logs you're looking for
1. In Grafana Click `Explore` in the menu
1. Use the drop down to select your log data source
1. Select the time frame on the top right (e.g. Last 1 hour)
1. Click `Label browser` in the query section
1. Choose the `shoestring_solution` and `service_module` labels and then select the specific ones you are interested in from the list below.
1. Click `Show logs`
1. Scroll down to see a section with a summary graph and then a second section with the actual log entries
> If you need to - you can select download on the top right of the log entries section