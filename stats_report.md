# Churn Statistical Analysis

Dataset: 10,000 customers, 6,947 churned (69.5%).


## 1. Descriptive statistics

|                         |     count |   mean |    std |   min |    25% |    50% |    75% |    max |
|:------------------------|----------:|-------:|-------:|------:|-------:|-------:|-------:|-------:|
| Contract Duration       | 10000.000 | 10.424 |  7.632 | 0.000 |  0.000 | 12.000 | 12.000 | 24.000 |
| Competitors             | 10000.000 |  0.852 |  0.366 | 0.000 |  1.000 |  1.000 |  1.000 |  2.000 |
| Tenure Months           | 10000.000 | 17.708 | 12.618 | 0.000 | 10.348 | 12.779 | 23.661 | 67.937 |
| Months Since Activation | 10000.000 | 33.444 | 15.565 | 8.016 | 21.025 | 33.903 | 46.813 | 67.970 |
| Churned                 | 10000.000 |  0.695 |  0.461 | 0.000 |  0.000 |  1.000 |  1.000 |  1.000 |


### Churn rate by factor (with 95% Wilson CI)

|                          |        n |   Churn rate |   CI low |   CI high |
|:-------------------------|---------:|-------------:|---------:|----------:|
| ('Cohort', 2020)         |  783.000 |        0.852 |    0.825 |     0.875 |
| ('Cohort', 2021)         | 2069.000 |        0.827 |    0.811 |     0.843 |
| ('Cohort', 2022)         | 2566.000 |        0.802 |    0.786 |     0.817 |
| ('Cohort', 2023)         | 2153.000 |        0.749 |    0.730 |     0.767 |
| ('Cohort', 2024)         | 2429.000 |        0.370 |    0.351 |     0.389 |
| ('City', 'Leeds')        |  683.000 |        0.824 |    0.794 |     0.851 |
| ('City', 'London')       | 5112.000 |        0.626 |    0.613 |     0.639 |
| ('City', 'Manchester')   | 4053.000 |        0.770 |    0.757 |     0.783 |
| ('City', 'Nottingham')   |  152.000 |        0.414 |    0.339 |     0.494 |
| ('District', 'E14')      | 3029.000 |        0.710 |    0.694 |     0.726 |
| ('District', 'E20')      |    1.000 |        1.000 |    0.207 |     1.000 |
| ('District', 'LS9')      |  683.000 |        0.824 |    0.794 |     0.851 |
| ('District', 'M15')      | 4053.000 |        0.770 |    0.757 |     0.783 |
| ('District', 'NG1')      |  152.000 |        0.414 |    0.339 |     0.494 |
| ('District', 'SW11')     |  845.000 |        0.652 |    0.619 |     0.683 |
| ('District', 'SW17')     |  214.000 |        0.397 |    0.334 |     0.464 |
| ('District', 'SW3')      |  318.000 |        0.025 |    0.013 |     0.049 |
| ('District', 'SW6')      |  113.000 |        0.575 |    0.483 |     0.662 |
| ('District', 'W3')       |  569.000 |        0.596 |    0.555 |     0.635 |
| ('District', 'W4')       |   23.000 |        0.043 |    0.008 |     0.210 |
| ('Contract', '12-month') | 5783.000 |        0.735 |    0.724 |     0.747 |
| ('Contract', '24-month') | 1452.000 |        0.425 |    0.400 |     0.451 |
| ('Contract', 'Monthly')  | 2765.000 |        0.751 |    0.735 |     0.767 |
| ('Competitors', 0)       | 1518.000 |        0.665 |    0.641 |     0.688 |
| ('Competitors', 1)       | 8442.000 |        0.701 |    0.691 |     0.710 |
| ('Competitors', 2)       |   40.000 |        0.575 |    0.422 |     0.715 |


## 2. Correlation and association analysis

Method selection:
- **Point-biserial** (mathematically identical to Pearson with a 0/1 variable) for *churn (binary)* vs numeric/ordinal predictors: contract duration, number of competitors, cohort year, months since activation.
- **Phi coefficient** for binary vs binary (churn vs has-competitor).
- **Chi-square + Cramér's V** for churn vs *nominal* factors (city, postcode district, contract type, bundle).
- **Pearson** only between two numeric/ordinal predictors (with Spearman as a rank-based robustness check).
- Tenure is excluded from predictors: it is only observed at termination and is therefore a *consequence* of churn (leakage), not a driver.


### 2a. Point-biserial correlations: churn vs numeric predictors

| Predictor               |       r |   p-value | Method         |
|:------------------------|--------:|----------:|:---------------|
| Contract Duration       | -0.1871 |    0.0000 | point-biserial |
| Competitors             |  0.0242 |    0.0156 | point-biserial |
| Cohort                  | -0.3412 |    0.0000 | point-biserial |
| Months Since Activation |  0.3404 |    0.0000 | point-biserial |
| Has Competitor (0/1)    |  0.0276 |    0.0058 | phi            |


### 2b. Chi-square tests and Cramér's V: churn vs categorical factors

| Factor      |      chi2 |     dof |   p-value |   Cramér's V |
|:------------|----------:|--------:|----------:|-------------:|
| Cohort      | 1641.7660 |  4.0000 |    0.0000 |       0.4052 |
| District    | 1070.5220 | 10.0000 |    0.0000 |       0.3272 |
| Contract    |  585.0427 |  2.0000 |    0.0000 |       0.2419 |
| City        |  331.3323 |  3.0000 |    0.0000 |       0.1820 |
| Bundle      |  115.8886 |  8.0000 |    0.0000 |       0.1077 |
| Competitors |   10.5634 |  2.0000 |    0.0051 |       0.0325 |


### 2c. Pearson / Spearman among numeric predictors

Pearson:

|                         |   Contract Duration |   Competitors |   Cohort |   Months Since Activation |
|:------------------------|--------------------:|--------------:|---------:|--------------------------:|
| Contract Duration       |               1.000 |        -0.059 |   -0.043 |                     0.039 |
| Competitors             |              -0.059 |         1.000 |   -0.019 |                     0.019 |
| Cohort                  |              -0.043 |        -0.019 |    1.000 |                    -0.979 |
| Months Since Activation |               0.039 |         0.019 |   -0.979 |                     1.000 |

Spearman:

|                         |   Contract Duration |   Competitors |   Cohort |   Months Since Activation |
|:------------------------|--------------------:|--------------:|---------:|--------------------------:|
| Contract Duration       |               1.000 |        -0.060 |   -0.047 |                     0.044 |
| Competitors             |              -0.060 |         1.000 |   -0.016 |                     0.016 |
| Cohort                  |              -0.047 |        -0.016 |    1.000 |                    -0.974 |
| Months Since Activation |               0.044 |         0.016 |   -0.974 |                     1.000 |


## 3. Logistic regression (explanatory) — odds ratios

Reference levels: Cohort 2020, City London, Contract Monthly, Competitors 0. District is nested within City, so a separate district-only model is shown.

|                      |   Odds ratio |   CI low |   CI high |   p-value |
|:---------------------|-------------:|---------:|----------:|----------:|
| Intercept            |        8.893 |    6.509 |    12.149 |     0.000 |
| Cohort[T.2021]       |        0.978 |    0.768 |     1.244 |     0.854 |
| Cohort[T.2022]       |        0.838 |    0.663 |     1.058 |     0.137 |
| Cohort[T.2023]       |        0.555 |    0.440 |     0.702 |     0.000 |
| Cohort[T.2024]       |        0.093 |    0.074 |     0.118 |     0.000 |
| City[T.London]       |        0.815 |    0.653 |     1.016 |     0.069 |
| City[T.Manchester]   |        1.526 |    1.215 |     1.916 |     0.000 |
| City[T.Nottingham]   |        0.377 |    0.244 |     0.583 |     0.000 |
| Contract[T.12-month] |        0.804 |    0.715 |     0.905 |     0.000 |
| Contract[T.24-month] |        0.174 |    0.149 |     0.204 |     0.000 |
| Competitors[T.1]     |        0.891 |    0.775 |     1.024 |     0.105 |
| Competitors[T.2]     |        0.899 |    0.432 |     1.871 |     0.776 |

Pseudo R² (McFadden): 0.197; LLR p-value: 0.00e+00


### District odds ratios (reference E14, London; districts with n<20 omitted)

|      |   Odds ratio |   p-value |
|:-----|-------------:|----------:|
| SW3  |        0.024 |     0.000 |
| W4   |        0.104 |     0.029 |
| SW17 |        0.327 |     0.000 |
| NG1  |        0.357 |     0.000 |
| W3   |        0.557 |     0.000 |
| SW11 |        0.863 |     0.131 |
| SW6  |        0.868 |     0.605 |
| LS9  |        0.965 |     0.758 |
| M15  |        1.326 |     0.000 |


## 4. Predictive modelling

| Model               |   CV AUC mean |   CV AUC sd |   Test AUC |   Test accuracy |   Brier |
|:--------------------|--------------:|------------:|-----------:|----------------:|--------:|
| Logistic regression |         0.796 |       0.015 |      0.792 |           0.779 |   0.157 |
| Gradient boosting   |         0.808 |       0.011 |      0.803 |           0.777 |   0.156 |

Baseline (predict majority class) accuracy: 0.695. Baseline Brier: 0.212.

Selected model: **Gradient boosting**.

```
              precision    recall  f1-score   support

      Active       0.65      0.57      0.61       763
     Churned       0.82      0.87      0.84      1737

    accuracy                           0.78      2500
   macro avg       0.74      0.72      0.73      2500
weighted avg       0.77      0.78      0.77      2500
```


### Permutation importance (drop in hold-out AUC when factor is shuffled)

| Factor      |   AUC drop (mean) |     sd |
|:------------|------------------:|-------:|
| Cohort      |            0.1667 | 0.0053 |
| Contract    |            0.0781 | 0.0056 |
| District    |            0.0494 | 0.0045 |
| City        |            0.0051 | 0.0019 |
| Competitors |            0.0036 | 0.0013 |


### Calibration (deciles of predicted probability)

|   decile |   predicted |   observed |       n |
|---------:|------------:|-----------:|--------:|
|        0 |       0.187 |      0.212 | 260.000 |
|        1 |       0.408 |      0.403 | 290.000 |
|        2 |       0.529 |      0.558 | 231.000 |
|        3 |       0.702 |      0.616 | 229.000 |
|        4 |       0.799 |      0.775 | 240.000 |
|        5 |       0.839 |      0.840 | 287.000 |
|        6 |       0.869 |      0.873 | 260.000 |
|        7 |       0.896 |      0.897 | 359.000 |
|        8 |       0.916 |      0.979 |  97.000 |
|        9 |       0.924 |      0.907 | 247.000 |


## 5. Example scenario predictions (selected model)

|                                                |   P(churn) |
|:-----------------------------------------------|-----------:|
| ('2024', 'London', 'E14', '24-month', '1')     |      0.209 |
| ('2024', 'London', 'E14', 'Monthly', '1')      |      0.743 |
| ('2023', 'Manchester', 'M15', '12-month', '1') |      0.868 |
| ('2022', 'Leeds', 'LS9', 'Monthly', '1')       |      0.864 |
| ('2021', 'Nottingham', 'NG1', '24-month', '0') |      0.313 |
| ('2020', 'London', 'SW11', '12-month', '0')    |      0.922 |


## 6. Notes for the churn-calculator app

- `churn_model.joblib` holds a dict: `model` (sklearn Pipeline, expects a DataFrame with columns ['Cohort', 'City', 'District', 'Contract', 'Competitors']; all values as strings), `levels` (valid values per factor incl. `District by City`), `base_rate`.
- Call `predict_churn(cohort, city, district, contract, competitors)` in `churn_model.py` to get a probability.
- Probabilities reflect this churn-weighted sample (base rate ~69%); for a live base, recalibrate the intercept to the true churn rate.
- Recent cohorts (2024) have had less exposure time; cohort captures both vintage and censoring effects.
