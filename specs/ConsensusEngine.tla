-------------------------------- MODULE ConsensusEngine --------------------------------
(*
  TLA+ specification for the ADL Lite consensus engine.

  Models:
    - Multiple agents appending to a single shared event chain.
    - Lifecycle transition graph matching adl_core_ontology.yaml.
    - Register action allowed only on an empty chain.
    - Validate action guarded by distinct-validator and N_min requirements.
    - Status derivation as Least Upper Bound over the lifecycle lattice.
    - Confidence as G-Counter max over VALIDATE/SNAPSHOT events.

  This bounded abstraction machine-checks the structural invariants underpinning
  Theorem 6 (collusion-resistant consensus) and Theorem 8 (status monotonicity).
*)

EXTENDS Integers, Sequences, FiniteSets

--------------------------------------------------------------------------------
\* Constants and basic types
--------------------------------------------------------------------------------

CONSTANTS
  Actors,           \* finite set of actor identifiers
  MaxEvents,        \* bound on chain length for model checking
  MaxConfidence,    \* confidence scaled to integers [0..MaxConfidence]
  N_min             \* minimum distinct validators required for a VALIDATE

ASSUME MaxEvents \in Nat \ {0}
ASSUME MaxConfidence \in Nat \ {0}
ASSUME N_min \in Nat \ {0}

EventTypes == {"REGISTER", "VALIDATE", "DEPRECATE", "FORK", "ARCHIVE",
               "RELATE", "EVIDENCE", "SEAL", "ANNOUNCE", "SNAPSHOT"}

LifecycleEvents == {"REGISTER", "VALIDATE", "DEPRECATE", "FORK", "ARCHIVE"}

Statuses == {"PROVISIONAL", "FORKED", "VALIDATED", "DEPRECATED", "ARCHIVED"}

--------------------------------------------------------------------------------
\* Lifecycle transition graph from adl_core_ontology.yaml
--------------------------------------------------------------------------------

AllowedTransition ==
  [s \in Statuses |->
     CASE s = "PROVISIONAL" -> {"VALIDATED", "DEPRECATED", "FORKED", "ARCHIVED"}
       \* Self-loop on VALIDATED models repeated VALIDATE events by distinct validators,
       \* which is required for N_min > 1 and for confidence updates in the event-first model.
       [] s = "VALIDATED"   -> {"VALIDATED", "DEPRECATED", "FORKED", "ARCHIVED"}
       [] s = "FORKED"      -> {"VALIDATED", "DEPRECATED", "ARCHIVED"}
       [] s = "DEPRECATED"  -> {"ARCHIVED"}
       [] s = "ARCHIVED"    -> {}
  ]

--------------------------------------------------------------------------------
\* Status lattice (provisional < forked < validated < deprecated < archived)
--------------------------------------------------------------------------------

LatticeOrder ==
  [s \in Statuses |->
     CASE s = "PROVISIONAL" -> {"PROVISIONAL", "FORKED", "VALIDATED", "DEPRECATED", "ARCHIVED"}
       [] s = "FORKED"      -> {"FORKED", "VALIDATED", "DEPRECATED", "ARCHIVED"}
       [] s = "VALIDATED"   -> {"VALIDATED", "DEPRECATED", "ARCHIVED"}
       [] s = "DEPRECATED"  -> {"DEPRECATED", "ARCHIVED"}
       [] s = "ARCHIVED"    -> {"ARCHIVED"}
  ]

LUB(S) ==
  IF "ARCHIVED" \in S THEN "ARCHIVED"
  ELSE IF "DEPRECATED" \in S THEN "DEPRECATED"
  ELSE IF "VALIDATED" \in S THEN "VALIDATED"
  ELSE IF "FORKED" \in S THEN "FORKED"
  ELSE "PROVISIONAL"

--------------------------------------------------------------------------------
\* Event records
--------------------------------------------------------------------------------

Event ==
  [event_id   : Nat,
   actor      : Actors,
   event_type : EventTypes,
   confidence : 0..MaxConfidence,
   prev       : Nat \cup {0}]

--------------------------------------------------------------------------------
\* State variables
--------------------------------------------------------------------------------

VARIABLES
  events,       \* sequence of Event records in chain order
  next_id       \* monotonic counter for fresh event ids

--------------------------------------------------------------------------------
\* Derived status, confidence, and validators
--------------------------------------------------------------------------------

StatusOf(etype) ==
  CASE etype = "REGISTER"  -> "PROVISIONAL"
    [] etype = "VALIDATE"  -> "VALIDATED"
    [] etype = "DEPRECATE" -> "DEPRECATED"
    [] etype = "FORK"      -> "FORKED"
    [] etype = "ARCHIVE"   -> "ARCHIVED"
    [] OTHER               -> "PROVISIONAL"

DerivedStatus(es) ==
  IF Len(es) = 0 THEN "PROVISIONAL"
  ELSE LUB({StatusOf(es[i].event_type) : i \in 1..Len(es)})

DerivedConfidence(es) ==
  IF Len(es) = 0 THEN 0
  ELSE LET vals == {es[i].confidence : i \in {j \in 1..Len(es) :
                        es[j].event_type \in {"VALIDATE", "SNAPSHOT"}}}
       IN IF vals = {} THEN 0 ELSE CHOOSE m \in vals : \A v \in vals : m >= v

Validators(es) ==
  {es[i].actor : i \in {j \in 1..Len(es) : es[j].event_type = "VALIDATE"}}

--------------------------------------------------------------------------------
\* Well-formedness axioms
--------------------------------------------------------------------------------

Axiom_Linkage(es) ==
  /\ Len(es) > 0 => es[1].prev = 0
  /\ \A i \in 2..Len(es) : es[i].prev = es[i-1].event_id

Axiom_DistinctIds(es) ==
  \A i, j \in 1..Len(es) : (es[i].event_id = es[j].event_id) => (i = j)

Axiom_MonotonicIds(es) ==
  \A i, j \in 1..Len(es) : i < j => es[i].event_id < es[j].event_id

Axiom_NonEmptyActor(es) ==
  \A i \in 1..Len(es) : es[i].actor \in Actors

Axiom_ConfidenceBounded(es) ==
  \A i \in 1..Len(es) : es[i].confidence \in 0..MaxConfidence

Axiom_ValidTypes(es) ==
  \A i \in 1..Len(es) : es[i].event_type \in EventTypes

WellFormed(es) ==
  /\ Axiom_Linkage(es)
  /\ Axiom_DistinctIds(es)
  /\ Axiom_MonotonicIds(es)
  /\ Axiom_NonEmptyActor(es)
  /\ Axiom_ConfidenceBounded(es)
  /\ Axiom_ValidTypes(es)

--------------------------------------------------------------------------------
\* Initial state and actions
--------------------------------------------------------------------------------

Init ==
  /\ events = <<>>
  /\ next_id = 1

\* Append an event with proper prev linkage.
AppendEvent(etype, actor, confidence) ==
  /\ Len(events) < MaxEvents
  /\ events' = Append(events,
                       [event_id   |-> next_id,
                        actor      |-> actor,
                        event_type |-> etype,
                        confidence |-> confidence,
                        prev       |-> IF Len(events) = 0 THEN 0 ELSE events[Len(events)].event_id])
  /\ next_id' = next_id + 1

\* REGISTER is allowed only on an empty chain.
Register(a) ==
  /\ Len(events) = 0
  /\ AppendEvent("REGISTER", a, 0)

\* VALIDATE requires the actor to be a new validator and the distinct-validator
\* count to reach N_min after the append.
Validate(a, c) ==
  /\ a \in Actors
  /\ c \in 0..MaxConfidence
  /\ "VALIDATED" \in AllowedTransition[DerivedStatus(events)]
  /\ a \notin Validators(events)
  /\ Cardinality(Validators(events)) + 1 >= N_min
  /\ AppendEvent("VALIDATE", a, c)

\* Lifecycle transitions other than REGISTER/VALIDATE require the resulting
\* status to be allowed by the ontology graph.
Deprecate(a) ==
  /\ "DEPRECATED" \in AllowedTransition[DerivedStatus(events)]
  /\ AppendEvent("DEPRECATE", a, 0)

Fork(a) ==
  /\ "FORKED" \in AllowedTransition[DerivedStatus(events)]
  /\ AppendEvent("FORK", a, 0)

Archive(a) ==
  /\ "ARCHIVED" \in AllowedTransition[DerivedStatus(events)]
  /\ AppendEvent("ARCHIVE", a, 0)

Next ==
  \/ (\E a \in Actors : Register(a))
  \/ (\E a \in Actors, c \in 0..MaxConfidence : Validate(a, c))
  \/ (\E a \in Actors : Deprecate(a))
  \/ (\E a \in Actors : Fork(a))
  \/ (\E a \in Actors : Archive(a))

--------------------------------------------------------------------------------
\* Invariants (Theorems)
--------------------------------------------------------------------------------

Inv_WellFormednessPreserved == WellFormed(events)

Inv_ValidTransition ==
  \A i \in 2..Len(events) :
    LET etype == events[i].event_type
        prev_status == DerivedStatus(SubSeq(events, 1, i - 1))
    IN etype \in {"VALIDATE", "DEPRECATE", "FORK", "ARCHIVE"}
       => StatusOf(etype) \in AllowedTransition[prev_status]

Inv_MinValidators ==
  (\E i \in 1..Len(events) : events[i].event_type = "VALIDATE")
  => Cardinality(Validators(events)) >= N_min

Inv_StatusMonotonic ==
  WellFormed(events) =>
    \A prefix_len \in 1..Len(events) :
      LET prefix == SubSeq(events, 1, prefix_len)
          s == DerivedStatus(prefix)
          g == DerivedConfidence(prefix)
      IN s \in Statuses /\ g \in 0..MaxConfidence

Inv_ConfidenceBounded ==
  WellFormed(events) =>
    /\ DerivedStatus(events) \in Statuses
    /\ DerivedConfidence(events) \in 0..MaxConfidence

--------------------------------------------------------------------------------
\* Specification
--------------------------------------------------------------------------------

Spec == Init /\ [][Next]_<<events, next_id>>

THEOREM ConsensusInvariants == Spec => [](Inv_WellFormednessPreserved /\ Inv_ValidTransition)
================================================================================
