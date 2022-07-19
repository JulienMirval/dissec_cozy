import plotly_express as px
from dash import html, dcc, dash
import numpy as np
import pandas as pd
import json
from glob import glob


def get_data(path):
    if ".json" in path:
        with open(path) as f:
            data = json.load(f)

        df = pd.concat([pd.DataFrame(i) for i in data])
    else:
        df = pd.read_csv(path, sep=";")

    df.rename(
        mapper={
            "seed": "run_id",
            "failureRate": "failure_probability",
            "observedFailureRate": "failure_rate",
            "emissionTime": "emitter_time",
            "receptionTime": "receiver_time",
            "emitterId": "emitter_id",
            "receiverId": "receiver_id",
            "latency": "simulation_length",
            "work": "total_work",
            "groupSize": "group_size",
        },
        axis=1,
        inplace=True,
    )
    df.reset_index(inplace=True)

    return df


def generate_graphs(data, strategies_map, tab="failure_probability"):
    graphs = dict()

    failure_probabilities = np.sort(pd.unique(data["failure_probability"]))
    group_sizes = np.sort(pd.unique(data["group_size"]))

    # Boxes
    graphs["work_failure_rate_status"] = px.box(
        data,
        x=tab,
        y="total_work",
        color="status",
        hover_name="run_id",
        points="all",
        title="Travail selon la taille de groupe par status",
    )
    graphs["work_failure_rate_strategy"] = px.box(
        data,
        x=tab,
        y="total_work",
        color="strategy",
        hover_name="run_id",
        points="all",
        title=f"Travail selon {'la probabilité de panne' if tab == 'failure_probability' else 'la taille de groupe'} par stratégie",
    )
    graphs["latency_failure_rate_status"] = px.box(
        data,
        x=tab,
        y="simulation_length",
        color="status",
        hover_name="run_id",
        points="all",
        title=f"Latence selon {'la probabilité de panne' if tab == 'failure_probability' else 'la taille de groupe'} par status",
    )
    graphs["latency_failure_rate_strategy"] = px.box(
        data,
        x=tab,
        y="simulation_length",
        color="strategy",
        hover_name="run_id",
        points="all",
        title=f"Latence selon {'la probabilité de panne' if tab == 'failure_probability' else 'la taille de groupe'} par stratégie",
    )
    graphs["observed_failure_rate_per_failure_prob"] = px.box(
        data,
        x=tab,
        y="failure_rate",
        color="strategy",
        hover_name="run_id",
        points="all",
        title=f"Taux de panne pour chaque {'probabilité de panne' if tab == 'failure_probability' else 'taille de groupe'}",
    )
    graphs["observed_failure_rate_per_status"] = px.box(
        data,
        x="status",
        y="failure_rate",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Taux de panne pour chaque statut d'exécution",
    )

    amps = data.copy()
    amps["total_work"] /= amps.groupby([tab, "strategy"], as_index=False).mean()[
        "total_work"
    ][0]
    amps["simulation_length"] /= amps.groupby([tab, "strategy"], as_index=False).mean()[
        "simulation_length"
    ][0]

    grouped_mean = data.groupby([tab, "strategy"], as_index=False).mean()
    grouped_upper = data.groupby([tab, "strategy"], as_index=False).max()
    grouped_upper["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_upper["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]
    grouped_lower = data.groupby([tab, "strategy"], as_index=False).min()
    grouped_lower["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_lower["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]
    grouped_mean["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_mean["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]

    for strat in strategies_map:
        graphs[f"{strategies_map[strat]}_length_scatter"] = px.scatter(
            data[data["strategy"] == strat],
            x="simulation_length",
            y="failure_rate",
            color="status",
            hover_name="run_id",
            title=f"{strategies_map[strat]} execution latency",
        )
        graphs[f"{strategies_map[strat]}_work_scatter"] = px.scatter(
            data[data["strategy"] == strat],
            x="simulation_length",
            y="total_work",
            color="status",
            hover_name="run_id",
            title=f"{strategies_map[strat]} total work",
        )

        graphs[f"{strategies_map[strat]}_latency_amplification_scatter"] = px.scatter(
            amps[amps["strategy"] == strat],
            x=tab,
            y="simulation_length",
            color="status",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} latency amplification",
        )
        graphs[f"{strategies_map[strat]}_work_amplification_scatter"] = px.scatter(
            amps[amps["strategy"] == strat],
            x=tab,
            y="total_work",
            color="status",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} work amplification",
        )
        graphs[f"{strategies_map[strat]}_completeness_scatter"] = px.scatter(
            amps[amps["strategy"] == strat],
            x=tab,
            y="completeness",
            color="status",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} completeness",
        )

        not_empty = len(grouped_mean[grouped_mean["strategy"] == strat]) > 0
        fallback = [0 for _ in failure_probabilities]
        d1 = {}
        d1[tab] = failure_probabilities if tab == "failure_probability" else group_sizes
        d1["mean"] = (
            grouped_mean[grouped_mean["strategy"] == strat]["simulation_length"]
            if not_empty
            else fallback
        )
        d1["upper"] = (
            grouped_upper[grouped_upper["strategy"] == strat]["simulation_length"]
            if not_empty
            else fallback
        )
        d1["lower"] = (
            grouped_lower[grouped_lower["strategy"] == strat]["simulation_length"]
            if not_empty
            else fallback
        )
        graphs[f"{strategies_map[strat]}_latency_amplification"] = px.line(
            d1,
            x=tab,
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} latency amplification",
        )
        d2 = {}
        d2[tab] = failure_probabilities if tab == "failure_probability" else group_sizes
        d2["mean"] = (
            grouped_mean[grouped_mean["strategy"] == strat]["total_work"]
            if not_empty
            else fallback
        )
        d2["upper"] = (
            grouped_upper[grouped_upper["strategy"] == strat]["total_work"]
            if not_empty
            else fallback
        )
        d2["lower"] = (
            grouped_lower[grouped_lower["strategy"] == strat]["total_work"]
            if not_empty
            else fallback
        )
        graphs[f"{strategies_map[strat]}_work_amplification"] = px.line(
            d2,
            x=tab,
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} work amplification",
        )
        d3 = {}
        d3[tab] = failure_probabilities if tab == "failure_probability" else group_sizes
        d3["mean"] = (
            grouped_mean[grouped_mean["strategy"] == strat]["completeness"]
            if not_empty
            else fallback
        )
        d3["upper"] = (
            grouped_upper[grouped_upper["strategy"] == strat]["completeness"]
            if not_empty
            else fallback
        )
        d3["lower"] = (
            grouped_lower[grouped_lower["strategy"] == strat]["completeness"]
            if not_empty
            else fallback
        )
        graphs[f"{strategies_map[strat]}_completeness"] = px.line(
            d3,
            x=tab,
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} completeness",
        )

    gmean = data.groupby([tab, "strategy"], as_index=False).mean()
    tmp_std = data.groupby([tab, "strategy"], as_index=False).std()
    gmean["total_work_std"] = tmp_std["total_work"]
    gmean["simulation_length_std"] = tmp_std["simulation_length"]
    gmean["completeness_std"] = tmp_std["completeness"]

    graphs["work_failure_prob_strategy"] = px.line(
        gmean,
        x=tab,
        y="total_work",
        error_y="total_work_std",
        color="strategy",
        markers=True,
        title="Average work per strategy",
    )
    graphs["latency_failure_prob_strategy"] = px.line(
        gmean,
        x=tab,
        y="simulation_length",
        error_y="simulation_length_std",
        color="strategy",
        markers=True,
        title="Average latency per strategy",
    )
    graphs["completeness_failure_prob_strategy"] = px.line(
        gmean,
        x=tab,
        y="completeness",
        error_y="completeness_std",
        color="strategy",
        markers=True,
        title="Average completeness per strategy",
    )

    graphs["completeness_per_failure_prob"] = px.box(
        data,
        x=tab,
        y="completeness",
        color="strategy",
        hover_name="run_id",
        points="all",
        title=f"Complétude par {'probabilité de panne' if tab == 'failure_probability' else 'taille de groupe'}",
    )

    return graphs


if __name__ == "__main__":
    with open("./dissec.config.json") as f:
        config = json.load(f)

    data = get_data(config["defaultGraph"])

    run_ids = pd.unique(data["run_id"])
    strategies = pd.unique(data["strategy"])
    status = pd.unique(data["status"])
    data["failure_probability"] = data["failure_probability"].round(6)
    failure_probabilities = np.sort(pd.unique(data["failure_probability"]))
    failure_rates = np.sort(pd.unique(data["failure_rate"]))

    outputs = glob("./outputs/*")

    # Remove strategies not present in the data
    strategies_map = dict(EAGER="Eager", OPTI="Optimistic", PESS="Pessimistic")
    for k in set(strategies_map.keys()).difference(strategies):
        del strategies_map[k]

    graphs = generate_graphs(data, strategies_map)

    app = dash.Dash(__name__)

    app.layout = html.Div(
        children=[
            dcc.Tabs(
                id="tabs",
                value="failure_probability",
                children=[
                    dcc.Tab(label="Probabilité de panne", value="failure_probability"),
                    dcc.Tab(label="Taille de groupe", value="group_size"),
                ],
            ),
            html.Div(
                children=[
                    html.H1(
                        children=f"Simulation  task",
                        style={"textAlign": "center", "color": "#7FDBFF"},
                    ),
                    dcc.Dropdown(
                        id="file-select",
                        options=[
                            dict(label=output.split("/")[-1], value=output)
                            for output in outputs
                        ],
                        value=config["defaultGraph"],
                    ),
                ]
            ),
            html.Div(
                style={"justifyContent": "center"},
                children=[
                    html.H1("Overview:"),
                    html.Ul(
                        children=[
                            html.Li(
                                children=[
                                    f"There are {len(data.groupby('run_id'))} simulations. {len(data[data['status'] == 'Success'].groupby('run_id'))} success, {len(data[data['status'] != 'Success'].groupby('run_id'))} failures",
                                    html.Ul(
                                        children=[
                                            html.Li(
                                                children=f"""
                            {len(pd.unique(data[data['status'] == i]['run_id']))} have status {i}.
                            Theoretical failure rate (min={round(data[data['status'] == i]['failure_probability'].min() * 100, 2)}%;
                            avg={round(data[data['status'] == i]['failure_probability'].mean() * 100, 2)}%;
                            med={round(data[data['status'] == i]['failure_probability'].median() * 100, 2)}%;
                            max={round(data[data['status'] == i]['failure_probability'].max() * 100, 2)}%).
                            Observed failure rate (min={round(data[data['status'] == i]['failure_rate'].min() * 100, 2)}%;
                            avg={round(data[data['status'] == i]['failure_rate'].mean() * 100, 2)}%;
                            med={round(data[data['status'] == i]['failure_rate'].median() * 100, 2)}%;
                            max={round(data[data['status'] == i]['failure_rate'].max() * 100, 2)}%)
                            """
                                            )
                                            for i in status
                                        ]
                                    ),
                                ]
                            ),
                            html.Li(
                                children=[
                                    "Different strategies have been used:",
                                    html.Ul(
                                        children=[
                                            html.Li(
                                                children=[
                                                    f"{len(data[data['strategy'] == i])} runs using {i} strategy, {len(data.loc[(data['status'] == 'Success') & (data['strategy'] == i)])} success"
                                                ]
                                            )
                                            for i in strategies
                                        ]
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
            ),
            #
            # Boxes
            #
            html.H1("Boxes:"),
            html.Div(
                [
                    html.H3("Failure Probabilities"),
                    dcc.RangeSlider(
                        0,
                        failure_probabilities[-1],
                        failure_probabilities[1] - failure_probabilities[0]
                        if len(failure_probabilities) > 1
                        else None,
                        value=[0, failure_probabilities[-1]],
                        id="failure-probabilities-range",
                    ),
                ]
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(
                        id="work_failure_rate_status",
                        figure=graphs["work_failure_rate_status"],
                    ),
                    dcc.Graph(
                        id="work_failure_rate_strategy",
                        figure=graphs["work_failure_rate_strategy"],
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(
                        id="latency_failure_rate_status",
                        figure=graphs["latency_failure_rate_status"],
                    ),
                    dcc.Graph(
                        id="latency_failure_rate_strategy",
                        figure=graphs["latency_failure_rate_strategy"],
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(
                        id="observed_failure_rate_per_failure_prob",
                        figure=graphs["observed_failure_rate_per_failure_prob"],
                    ),
                    dcc.Graph(
                        id="observed_failure_rate_per_status",
                        figure=graphs["observed_failure_rate_per_status"],
                    ),
                ],
            ),
            #
            # Scatters
            #
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_length_scatter"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_work_scatter"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            #
            # Amplifications
            #
            html.H1("Amplifications:"),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_work_amplification"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_latency_amplification"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_completeness"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_latency_amplification_scatter"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_work_amplification_scatter"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(id=id, figure=graphs[id])
                    for id in [
                        f"{strategies_map[strat]}_completeness_scatter"
                        for strat in strategies_map.keys()
                    ]
                ],
            ),
            #
            # Rest
            #
            html.H1("Other graphs"),
            html.Div(
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "justify-content": "center",
                },
                children=[
                    dcc.Graph(
                        id=id,
                        figure=graphs[id],
                    )
                    for id in [
                        "completeness_failure_prob_strategy",
                        "work_failure_prob_strategy",
                        "latency_failure_prob_strategy",
                    ]
                ],
            ),
            dcc.Graph(
                id="completeness_per_failure_prob",
                figure=graphs["completeness_per_failure_prob"],
            ),
        ]
    )

    @app.callback(
        [dash.Output(component_id=id, component_property="figure") for id in graphs],
        [
            dash.Input(
                component_id="failure-probabilities-range", component_property="value"
            ),
            dash.Input(component_id="file-select", component_property="value"),
            dash.Input(component_id="tabs", component_property="value"),
        ],
    )
    def update_graphs(selected_failures, selected_file, tab):
        df = get_data(selected_file)

        df = df[
            (df["failure_probability"] >= selected_failures[0])
            & (df["failure_probability"] <= selected_failures[1])
        ]

        graphs = generate_graphs(df, strategies_map, tab)

        return [graphs[id] for id in graphs]

    app.run_server(debug=True)
