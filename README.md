# AI Influence Over Retail Financial Investment 

## Overview
With the widespread addoption & trust of GenAI in day to day life people naturally lean into trusting money to these tools to make financial decisions on these behalfs. For a good set of cases this is blind trust without understanding of the model and where it could be manipulated to obtain a specific outcome. 

## Abstract 
There are two primary vectors that I am focusing on for how a agent/model could be influenced towards making a specific dections. \n
* Pretraining by poisoning the sample data by dumping specific text material to be pulled into the model one is able to influnce the probability of a certain reccomendation. For example imagine a user asks the following what energy stock should I invest in and a malicious actor writes 1500+ documents on a specific penny stock then when the model is trained it will be weighted toward suggesting a product that isn't necessarilly the write choice. Same thought can be had towards pump and dump stocks or crypto
* Influencing SEO / Tool Calls to return specific context weighting towards a specific reccomendation.

## Methodology
To tackle these two vectors of attack going to go through two different experiments:
* Create a baseline set of prompts testing the baseline reccomendation of different related user queries based upon financial advice. These will be evaluated over opensource models such as gemma 3/4 gpt OSS and then it will be fine tuned on a curated set of articles written intending to influence the reccomendation. Will evaluate the different levels of fine tuning required to obtain this outcome.
* Will look into evaluating the traces performed by different model providers when asking related questions and will evaluate the surface vector and the ability for it to be exploited. 


