import plotly_express as px
from dash import html, dcc, dash
import numpy as np
import pandas as pd
import json


def get_data(path):
    with open(path) as f:
        data = json.load(f)

    df = pd.concat([pd.DataFrame(i) for i in data])
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
        },
        axis=1,
        inplace=True,
    )

    return df


if __name__ == "__main__":
    with open("./dissec.config.json") as f:
        config = json.load(f)

    data = get_data(config["dataPath"])

    run_ids = pd.unique(data["run_id"])
    strategies = pd.unique(data["strategy"])
    status = pd.unique(data["status"])
    data["failure_probability"] = data["failure_probability"].round(6)
    failure_probabilities = np.sort(pd.unique(data["failure_probability"]))
    failure_rates = np.sort(pd.unique(data["failure_rate"]))

    # Remove strategies not present in the data
    strategies_map = dict(EAGER="Eager", OPTI="Optimistic", PESS="Pessimistic")
    for k in set(strategies_map.keys()).difference(strategies):
        del strategies_map[k]

    # Boxes
    work_failure_rate_status_fig = px.box(
        data,
        x="failure_probability",
        y="total_work",
        color="status",
        hover_name="run_id",
        points="all",
        title="Travail selon le taux de panne par status",
    )
    work_failure_rate_strategy_fig = px.box(
        data,
        x="failure_probability",
        y="total_work",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Travail selon le taux de panne par stratégie",
    )
    latency_failure_rate_status_fig = px.box(
        data,
        x="failure_probability",
        y="simulation_length",
        color="status",
        hover_name="run_id",
        points="all",
        title="Latence selon le taux de panne par status",
    )
    latency_failure_rate_strategy_fig = px.box(
        data,
        x="failure_probability",
        y="simulation_length",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Latence selon le taux de panne par stratégie",
    )
    observed_failure_rate_per_failure_prob_fig = px.box(
        data,
        x="failure_probability",
        y="failure_rate",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Taux de panne pour chaque probabilité de panne",
    )
    observed_failure_rate_per_status_fig = px.box(
        data,
        x="status",
        y="failure_rate",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Taux de panne pour chaque statut d'exécution",
    )

    length_scatters = [
        px.scatter(
            data[data["strategy"] == strat],
            x="simulation_length",
            y="failure_rate",
            color="status",
            hover_name="run_id",
            title=f"{strategies_map[strat]} execution latency",
        )
        for strat in strategies_map
    ]
    work_scatters = [
        px.scatter(
            data[data["strategy"] == strat],
            x="simulation_length",
            y="total_work",
            color="status",
            hover_name="run_id",
            title=f"{strategies_map[strat]} total work",
        )
        for strat in strategies_map
    ]

    amps = data.copy()
    amps["total_work"] /= amps.groupby(
        ["failure_probability", "strategy"], as_index=False
    ).mean()["total_work"][0]
    amps["simulation_length"] /= amps.groupby(
        ["failure_probability", "strategy"], as_index=False
    ).mean()["simulation_length"][0]
    latency_amplification_scatters = [
        px.scatter(
            amps[amps["strategy"] == strat],
            x="failure_probability",
            y="simulation_length",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} latency amplification",
        )
        for strat in strategies_map
    ]
    work_amplification_scatters = [
        px.scatter(
            amps[amps["strategy"] == strat],
            x="failure_probability",
            y="total_work",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} work amplification",
        )
        for strat in strategies_map
    ]
    completeness_amplification_scatters = [
        px.scatter(
            amps[amps["strategy"] == strat],
            x="failure_probability",
            y="completeness",
            marginal_y="histogram",
            trendline="ols",
            title=f"{strategies_map[strat]} completeness",
        )
        for strat in strategies_map
    ]

    grouped_mean = data.groupby(
        ["failure_probability", "strategy"], as_index=False
    ).mean()
    grouped_upper = data.groupby(
        ["failure_probability", "strategy"], as_index=False
    ).max()
    grouped_upper["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_upper["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]
    grouped_lower = data.groupby(
        ["failure_probability", "strategy"], as_index=False
    ).min()
    grouped_lower["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_lower["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]
    grouped_mean["total_work"] /= grouped_mean["total_work"].iloc[0]
    grouped_mean["simulation_length"] /= grouped_mean["simulation_length"].iloc[0]

    latency_amplification_figs = [
        px.line(
            dict(
                failure_probability=failure_probabilities,
                mean=grouped_mean[grouped_mean["strategy"] == strat][
                    "simulation_length"
                ],
                upper=grouped_upper[grouped_upper["strategy"] == strat][
                    "simulation_length"
                ],
                lower=grouped_lower[grouped_lower["strategy"] == strat][
                    "simulation_length"
                ],
            ),
            x="failure_probability",
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} latency amplification",
        )
        for strat in strategies_map
    ]
    work_amplification_figs = [
        px.line(
            dict(
                failure_probability=failure_probabilities,
                mean=grouped_mean[grouped_mean["strategy"] == strat]["total_work"],
                upper=grouped_upper[grouped_upper["strategy"] == strat]["total_work"],
                lower=grouped_lower[grouped_lower["strategy"] == strat]["total_work"],
            ),
            x="failure_probability",
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} work amplification",
        )
        for strat in strategies_map
    ]
    completeness_amplification_figs = [
        px.line(
            dict(
                failure_probability=failure_probabilities,
                mean=grouped_mean[grouped_mean["strategy"] == strat]["completeness"],
                upper=grouped_upper[grouped_upper["strategy"] == strat]["completeness"],
                lower=grouped_lower[grouped_lower["strategy"] == strat]["completeness"],
            ),
            x="failure_probability",
            y=["mean", "lower", "upper"],
            markers=True,
            title=f"{strategies_map[strat]} completeness amplification",
        )
        for strat in strategies_map
    ]

    gmean = data.groupby(["failure_probability", "strategy"], as_index=False).mean()
    tmp_std = data.groupby(["failure_probability", "strategy"], as_index=False).std()
    gmean["total_work_std"] = tmp_std["total_work"]
    gmean["simulation_length_std"] = tmp_std["simulation_length"]
    gmean["completeness_std"] = tmp_std["completeness"]

    work_failure_prob_strategy_fig = px.line(
        gmean,
        x="failure_probability",
        y="total_work",
        error_y="total_work_std",
        color="strategy",
        markers=True,
        title="Average work per strategy",
    )
    latency_failure_prob_strategy_fig = px.line(
        gmean,
        x="failure_probability",
        y="simulation_length",
        error_y="simulation_length_std",
        color="strategy",
        markers=True,
        title="Average latency per strategy",
    )
    completeness_failure_prob_strategy_fig = px.line(
        gmean,
        x="failure_probability",
        y="completeness",
        error_y="completeness_std",
        color="strategy",
        markers=True,
        title="Average completeness per strategy",
    )

    completeness_per_failure_prob_fig = px.box(
        data,
        x="failure_probability",
        y="completeness",
        color="strategy",
        hover_name="run_id",
        points="all",
        title="Complétude par proba de pannes",
    )

    app = dash.Dash(__name__)

    app.layout = html.Div(
        children=[
            html.H1(
                children=f"Latency vs Reception time",
                style={"textAlign": "center", "color": "#7FDBFF"},
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
                        figure=work_failure_rate_status_fig,
                    ),
                    dcc.Graph(
                        id="work_failure_rate_strategy",
                        figure=work_failure_rate_strategy_fig,
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
                        figure=latency_failure_rate_status_fig,
                    ),
                    dcc.Graph(
                        id="latency_failure_rate_strategy",
                        figure=latency_failure_rate_strategy_fig,
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
                        figure=observed_failure_rate_per_failure_prob_fig,
                    ),
                    dcc.Graph(
                        id="observed_failure_rate_per_status",
                        figure=observed_failure_rate_per_status_fig,
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
                    dcc.Graph(
                        id=f"length_{strategies_map[key]}_scatter_plot", figure=scatter
                    )
                    for (key, scatter) in zip(strategies_map.keys(), length_scatters)
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
                        id=f"work_{strategies_map[key]}_scatter_plot", figure=scatter
                    )
                    for (key, scatter) in zip(strategies_map.keys(), work_scatters)
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
                    dcc.Graph(
                        id=f"{strategies_map[key]}_work_amplification", figure=scatter
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), work_amplification_figs
                    )
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
                        id=f"{strategies_map[key]}_latency_amplification",
                        figure=scatter,
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), latency_amplification_figs
                    )
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
                        id=f"{strategies_map[key]}_completeness_amplification",
                        figure=scatter,
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), completeness_amplification_figs
                    )
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
                        id=f"{strategies_map[key]}_latency_amplification_scatter",
                        figure=scatter,
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), latency_amplification_scatters
                    )
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
                        id=f"{strategies_map[key]}_work_amplification_scatter",
                        figure=scatter,
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), work_amplification_scatters
                    )
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
                        id=f"{strategies_map[key]}_completeness_amplification_scatter",
                        figure=scatter,
                    )
                    for (key, scatter) in zip(
                        strategies_map.keys(), completeness_amplification_scatters
                    )
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
                        id="completeness_failure_prob_strategy",
                        figure=completeness_failure_prob_strategy_fig,
                    ),
                    dcc.Graph(
                        id="work_failure_prob_strategy",
                        figure=work_failure_prob_strategy_fig,
                    ),
                    dcc.Graph(
                        id="latency_failure_prob_strategy",
                        figure=latency_failure_prob_strategy_fig,
                    ),
                ],
            ),
            dcc.Graph(id="completeness", figure=completeness_per_failure_prob_fig),
        ]
    )

    @app.callback(
        [
            dash.Output(
                component_id="work_failure_rate_status", component_property="figure"
            ),
            dash.Output(
                component_id="work_failure_rate_strategy", component_property="figure"
            ),
            dash.Output(
                component_id="latency_failure_rate_status", component_property="figure"
            ),
            dash.Output(
                component_id="latency_failure_rate_strategy",
                component_property="figure",
            ),
            dash.Output(
                component_id="observed_failure_rate_per_failure_prob",
                component_property="figure",
            ),
            dash.Output(
                component_id="observed_failure_rate_per_status",
                component_property="figure",
            ),
        ],
        [
            dash.Input(
                component_id="failure-probabilities-range", component_property="value"
            ),
        ],
    )
    def update_boxes(
        selected_failures,
    ):
        df = data.copy()

        df = df[
            df["failure_probability"].isin(
                [
                    i
                    for i in failure_probabilities
                    if i <= selected_failures[1] and i >= selected_failures[0]
                ]
            )
        ]

        group = df.groupby(["run_id", "status", "strategy"], as_index=False).mean()
        work_failure_rate_status_fig = px.box(
            group,
            x="failure_probability",
            y="total_work",
            color="status",
            hover_name="run_id",
            points="all",
            title="Travail selon le taux de panne par status",
        )
        work_failure_rate_strategy_fig = px.box(
            group,
            x="failure_probability",
            y="total_work",
            color="strategy",
            hover_name="run_id",
            points="all",
            title="Travail selon le taux de panne par stratégie",
        )
        latency_failure_rate_status_fig = px.box(
            group,
            x="failure_probability",
            y="simulation_length",
            color="status",
            hover_name="run_id",
            points="all",
            title="Latence selon le taux de panne par status",
        )
        latency_failure_rate_strategy_fig = px.box(
            group,
            x="failure_probability",
            y="simulation_length",
            color="strategy",
            hover_name="run_id",
            points="all",
            title="Latence selon le taux de panne par stratégie",
        )
        observed_failure_rate_per_failure_prob_fig = px.box(
            group,
            x="failure_probability",
            y="failure_rate",
            color="strategy",
            hover_name="run_id",
            points="all",
            title="Taux de panne pour chaque probabilité de panne",
        )
        observed_failure_rate_per_status_fig = px.box(
            group,
            x="status",
            y="failure_rate",
            color="strategy",
            hover_name="run_id",
            points="all",
            title="Taux de panne pour chaque statut d'exécution",
        )
        return [
            work_failure_rate_status_fig,
            work_failure_rate_strategy_fig,
            latency_failure_rate_status_fig,
            latency_failure_rate_strategy_fig,
            observed_failure_rate_per_failure_prob_fig,
            observed_failure_rate_per_status_fig,
        ]

    app.run_server(debug=True)
