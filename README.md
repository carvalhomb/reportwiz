# ReportWiz

An Intelligent Business Reporting Assistant

## Problem

### Problem description

Business departments struggle to quickly retrieve information and generate reports without relying on developers and business analysts even for simple queries. At the same time, business analytics departments are overloaded with repeated requests that have already been responded to multiple times, so less time is available to produce really new, useful reports and data analyses.

### Why 

This problem is worth solving because business departments need to access necessary information rapidly to increase their efficiency. Businesses often face delays and inefficiencies when non-technical users need simple reports but lack the skills to create SQL queries and the visualizations that they need. On the other end, business analytics departments are overloaded with such simple queries and have less time for more complex work.

### Audience

The primary users of this product are business departments, including analysts and managers, who need timely access to data for decision-making but do not have the technical skills to write SQL queries. Their pain point is the inefficiency and delay caused by relying on developers for simple reporting tasks, which this chatbot aims to resolve.

## Solution

Our solution to this problem is **ReportWiz**.

**Reportwiz** is a chatbot that is connected to a repository of existing reports that have been produced, and to the in-house datamarts that contain the company's business-relevant data. It takes requests for information from business users and intelligently decides what to do. When **ReportWiz** receives a request from the user:

- If there is already a report, it points the user to the existing report;
- If the report does not exist, it generates the required SQL code to give the requested information to the user;
- If it is not able to find the requested information, it creates a structured request (i.e. JIRA ticket) that will be dispatched to the business analytics department so that a report can be produced and added to the repository.

By enabling business users to use natural language to express what they need and retrieve the requested information (in the format of existing reports or SQL queries directly to the database), we can significantly reduce dependency on developers, streamline reporting processes, and improve overall productivity. For the business analytics department, it means less time responding to requests that have already been met and focusing their time in producing new, high quality reports when needed. For the company, it means more agile and responsive operations. For the world, it showcases the potential of AI to make data more accessible. For us, it’s a fulfilling challenge to use AI to bridge the gap between technical and non-technical users.

### Implementation details

**ReportWiz** is a LangChain-based chatbot that uses OpenAI's GPT-4o chat model in the background to receive and process the user's requests for information. 

This is how the application is structured:

![Application diagram](/chatbot_white.png?raw=true "Application diagram")

There is a main *Chatbot* that interacts with the user, taking their requests for information, and forwarding it to a second chat model (the *Retriever*). The *Retriever* has access to a *Toolbox*, which allows it to search for existing reports in PDF format indexed in a *Qdrant Vector Databas*e and to interact with the *Databas*e to search for up to date information.

Once the *Retriever* finishes its look up, it will return its findings to the *Chatbot*, who will relay the information to the user. If, however, the Retriever cannot find the information requested, its response will be routed to the third chatbot, the *Ticketing bot*, who will take care of preparing a structured request for the Business Analytics department that can be inputted in a ticketing system (e.g. JIRA).

#### Langgraph graph

As mentioned above, the application is implemented with [LangGraph](https://langchain-ai.github.io/langgraph/). LangGraph is a library for building stateful, multi-actor applications with LLMs, used to create agent and multi-agent workflows. It allows us to better control the flow of the application and offer a better user experience in the interaction with the LLM.

Here is a representation of **ReportWiz** as a graph, with nodes representing the functions that our application performs, and the edges representing the transitions that can happen between these nodes:

![LangGraph diagram](/reportwiz_graph.png?raw=true "Langgraph nodes")


### Project success

Success for this project means the chatbot can accurately interpret natural language queries, verify if relevant reports, scripts or code already exist, and decide the best outcome. 

The key performance indicator (KPI) will be the reduction in time business departments spend on obtaining necessary information, aiming for a 50% decrease in the average time required for report generation.

## Future work

This Proof-of-concept has been produced using dummy data. However, the hardest part of the application is to do retrieval properly. And for that, we need to test it using real data and evaluate it properly. So, it is in our plans that, after the first version of the implementation, we will evaluate the need for fine-tuning of embeddings and of the LLM (Large Language Model) on our business data and existing code to improve the accuracy of the chatbot and its relevance to the company's data.

## Sharing

We plan to share our project with the AI and business analytics communities through platforms such as GitHub, relevant LinkedIn groups, and AI-focused forums. This will allow us to receive feedback, encourage collaboration, and contribute to the broader discussion on making data access more efficient and democratized through AI.
