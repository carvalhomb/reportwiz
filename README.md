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
- If it is not able to generate the query, it gathers all necessary information from the user to create a structured request (i.e. JIRA ticket) that will be dispatched to the business analytics department so that a report can be produced and added to the repository.

By enabling business users to use natural language to express what they need and retrieve the requested information (in the format of existing reports or SQL queries directly to the database), we can significantly reduce dependency on developers, streamline reporting processes, and improve overall productivity. For the business analytics department, it means less time responding to requests that have already been met and focusing their time in producing new, high quality reports when needed. For the company, it means more agile and responsive operations. For the world, it showcases the potential of AI to make data more accessible. For us, it’s a fulfilling challenge to use AI to bridge the gap between technical and non-technical users.

### Implementation details

The solution will leverage Retrieval-Augmented Generation (RAG) to retrieve information  from existing reports, scripts and code, and a Large Language Model (LLM) to understand the users' requests in natural language and decide the correct outcome.

The model will have access to a repository of previously generated reports, a schema of the database and sample SQL queries used to produce the types of reports that the business users typically need.

It is also relevant to note that we want the chatbot to "fail gracefully", that is, recognize when it is not able to provide responses for simple quests, and then include a human in the loop by gathering necessary details to create a request ticket for the reporting team.

After the first version of the implementation, we will evaluate the need for fine-tuning of embeddings and of the LLM (Large Language Model) on our business data and existing code to improve the accuracy of the chatbot and its relevance to the company's data.

### Success

Success for this project means the chatbot can accurately interpret natural language queries, verify if relevant reports, scripts or code already exist, and decide the best outcome. 

The key performance indicator (KPI) will be the reduction in time business departments spend on obtaining necessary information, aiming for a 50% decrease in the average time required for report generation.


## Sharing

We plan to share our project with the AI and business analytics communities through platforms such as GitHub, relevant LinkedIn groups, and AI-focused forums. This will allow us to receive feedback, encourage collaboration, and contribute to the broader discussion on making data access more efficient and democratized through AI.
