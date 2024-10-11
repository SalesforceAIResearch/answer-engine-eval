# Answer Engine Evaluation Framework

Code release that accompanies the paper pre-print "[Search Engines in an AI Era: The False Promise of Factual and Verifiable Source-Cited Responses]()". Note that data in this work can be used for research purpose only.

<p align="center">
  <img src="AEE_Intro_Figure.png" style="height: 300px;" /><br />
  <u>Caption:</u> Overview of the paper's contribution: a qualitative usability study, design recommendations, and a metric-based evaluation implemented as a score-card. 
</p>

The code in this repository enables the reproduction of the metrics-based results of the paper (Section 5), which is computed as follows:
<p align="center">
  <img src="AEE_Metrics_Figure.png" style="height: 400px;" /><br />
</p>

## Metric Computation

The main function that computes the prerequisites to compute scores is included in [populate_scores.py](https://github.com/SalesforceAIResearch/answer-engine-eval/blob/main/populate_scores.py).
It takes in as input a dataset file that contains user queries, as well as scraped results from various answer engines (e.g., [data/ans_eng_eval_0.1.json](https://github.com/SalesforceAIResearch/answer-engine-eval/blob/main/data/ans_eng_eval_0.1.json)).

## Visualizing Results

The notebook [Answer_Engine_Eval.ipynb](https://github.com/SalesforceAIResearch/answer-engine-eval/blob/main/Answer_Engine_Eval.ipynb) provides the scripts to produce results that correspond to the ones presented in the paper (see Figure below).

<p align="center">
  <img src="AEE_Metrics_Results.png" style="height: 400px;" /><br />
</p>

## Citation

TBA
