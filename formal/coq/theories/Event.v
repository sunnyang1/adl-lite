(* Event.v -- ADL Lite event model.
   Events are the atoms of an EventChain; status/confidence are derived. *)

Require Import List String.
Require Import ADL.Status.

Inductive adl_event_type : Set :=
  | REGISTER
  | VALIDATE
  | DEPRECATE
  | FORK
  | ARCHIVE
  | RELATE
  | EVIDENCE
  | SEAL
  | ANNOUNCE
  | SNAPSHOT.

Record event : Set := mkEvent {
  event_id    : nat;
  actor       : string;
  event_type  : adl_event_type;
  confidence  : nat;
  prev        : option nat
}.

(* Lifecycle event types determine the derived status. *)
Definition StatusOf (et : adl_event_type) : status :=
  match et with
  | REGISTER   => PROVISIONAL
  | VALIDATE   => VALIDATED
  | DEPRECATE  => DEPRECATED
  | FORK       => FORKED
  | ARCHIVE    => ARCHIVED
  | RELATE     => PROVISIONAL
  | EVIDENCE   => PROVISIONAL
  | SEAL       => VALIDATED
  | ANNOUNCE   => PROVISIONAL
  | SNAPSHOT   => VALIDATED
  end.
