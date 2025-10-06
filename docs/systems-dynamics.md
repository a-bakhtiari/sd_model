```mermaid
flowchart TD
    %% --- Classes ---
    classDef stock fill:#cde4ff,stroke:#444,stroke-width:2px
    classDef inflow fill:#e6ffe6,stroke:#444,stroke-dasharray: 5 5
    classDef outflow fill:#ffe6e6,stroke:#444,stroke-dasharray: 5 5
    classDef aux fill:#fff2cc,stroke:#444
    classDef delay fill:#eed,stroke:#bba,stroke-dasharray: 2 4
    classDef comment fill:#eee,stroke:#bbb,stroke-width:1.5px,font-style: italic

    %%--- STOCKS ---
    SourceCode[("Source Code")]:::stock
    Contributors[("Contributors")]:::stock
    CoreDevs[("Core Developers\n(Maintainers)")]:::stock
    Documentation[("Documentation")]:::stock

    %%--- INFLOWS CLOUDS ---
    MergeCommit>Merge/Commit]:::inflow
    JoinRate>Joining Rate]:::inflow
    PromotionRate>Promotion Rate]:::inflow
    DocMerge>Doc Merge]:::inflow

    %%--- OUTFLOWS CLOUDS ---
    Deprecation>Deprecation/\nDifferentiation]:::outflow
    TurnoverC>Turnover Rate]:::outflow
    Burnout>Turnover/Burnout]:::outflow
    DocObsol>Doc Obsolescence]:::outflow

    %%--- AUXILIARY VARS & DELAYS ---
    PullRequests["Pull Requests/\nIssues"]:::aux
    Complexity["Code Complexity"]:::aux
    MaintainerLoad["Maintainer Load"]:::aux
    Reputation["Project Reputation"]:::aux
    DocQuality["Doc Quality"]:::aux

    ReviewDelay{{"Review Delay:\nMaintainer load slows reviews\n(increases Contributor Turnover)"}}:::delay
    OnboardingDelay{{"Onboarding Delay:\nDriven by Doc Quality & Complexity"}}:::delay
    ReputationDelay{{"Reputation Delay:\nSlow-moving effect"}}:::delay
    CommonsNote{{"Tragedy of the Commons:\nCoreDev energy is a finite shared resource\n(Contrib. + PR pressure draw from this)"}}:::comment

    %%--- STOCK: Source Code ---
    MergeCommit-->|inflow|SourceCode
    SourceCode-->|outflow|Deprecation
    CoreDevs-->|"directly contribute"|MergeCommit

    %%-R1 (Feature Factory Loop): SourceCode=>PullRequests=>Merge=>SourceCode
    SourceCode-->|"more code\ngenerates"|PullRequests
    PullRequests-->|"drives more"|MergeCommit
    MergeCommit--.->|"feedback cycle (R1)"|SourceCode

    %%-B1 (Tech Debt Loop): SourceCode=>Complexity=>slows Merge
    SourceCode-->|"more code\nincreases"|Complexity
    Complexity-->|"slows inflow"|MergeCommit
    Complexity-->|"increases"|OnboardingDelay
    OnboardingDelay-->|"reduces effectiveness of"|JoinRate
    SourceCode-->|"growth increases outflow"|Deprecation

    %%--- STOCK: Contributors ---
    JoinRate-->|inflow|Contributors
    Contributors-->|outflow|TurnoverC
    Contributors-->|"get promoted via"|PromotionRate
    PromotionRate-->|inflow|CoreDevs

    %%-R2 (Project Buzz Loop): Contributors=>Reputation=>JoinRate
    Contributors-->|"help build"|Reputation
    Reputation-->|"improves"|ReputationDelay
    ReputationDelay-->|"boosts"|JoinRate
    JoinRate--.->|"feedback cycle (R2)"|Contributors

    %%-B2 (Onboarding Barrier): Complexity=>OnboardingDelay=>JoinRate
    Complexity-->|"makes joining harder"|OnboardingDelay
    OnboardingDelay-->|"reduces"|JoinRate

    %%-Contrib->Core Developers
    Contributors-->|"promoted via"|PromotionRate
    PromotionRate-->|inflow|CoreDevs

    %%--- STOCK: Core Developers (Maintainers) ---
    CoreDevs-->|outflow|Burnout

    %%-B3 (Burnout Loop): Contrib + PRs=>Maintainer Load=>Burnout
    Contributors-->|"need mentoring"|MaintainerLoad
    PullRequests-->|"needs review"|MaintainerLoad
    MaintainerLoad-->|"causes"|Burnout
    MaintainerLoad-->|"reduces mentorship\nand slows reviews"|ReviewDelay
    ReviewDelay-->|"increases"|TurnoverC
    MaintainerLoad-->|"limits"|PromotionRate

    %%-Maintainer Load negative feedback
    Burnout-->|"decreases\nCoreDev capacity"|CoreDevs

    %%--- STOCK: Documentation ---
    DocMerge-->|inflow|Documentation
    Documentation-->|outflow|DocObsol

    %%-Doc contributions & effect
    CoreDevs-->|"write & review"|DocMerge
    Contributors-->|"doc PRs"|DocMerge
    Documentation-->|"improves"|DocQuality

    %%-DocQuality effect on onboarding
    DocQuality-->|"reduces delay"|OnboardingDelay

    %%--- System Archetype & Comments ---
    CoreDevs--.->|draw from\nCommons|CommonsNote
    Contributors--.->|draw from\nCommons|CommonsNote
    PullRequests--.->|add pressure to\nCommons|CommonsNote

    %%--- CLASSES ---
    class SourceCode,Contributors,CoreDevs,Documentation stock
    class MergeCommit,JoinRate,PromotionRate,DocMerge inflow
    class Deprecation,TurnoverC,Burnout,DocObsol outflow
    class PullRequests,Complexity,MaintainerLoad,Reputation,DocQuality aux
    class ReviewDelay,OnboardingDelay,ReputationDelay delay
    class CommonsNote comment
    
```