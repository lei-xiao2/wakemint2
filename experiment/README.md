### experiment

The results of our conducted experiments.

#### Overview

- Results of large-scale experiment.
- Evaluation results of related experiments.
  - randomly sampled dataset with a confidence interval of 10 and a confidence level of 95% for **false negatives** evaluation.
  - labeled results for true positives, false positives and false negatives from the `negatives_samples`

#### Details

- `evaluation`: evaluation results of WakeMint.
  - `true_positives` and `false_positives`: classification and cases of true positives and false positives of WakeMint.
  - `false_negatives`: analysis and cases of false_negatives from `negatives_samples`
- ``negatives_samples``: randomly sampled dataset with a confidence interval of 10 and a confidence level of 95% on contracts were not reported.
- `sleepminting.csv`: contract addresses and corresponding detection results.