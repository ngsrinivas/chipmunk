grammar instruction;

// Hide whitespace, but don't skip it
WS : [ \n\t\r]+ -> channel(HIDDEN);

// Identifiers
ID : ('a'..'z' | 'A'..'Z') ('a'..'z' | 'A'..'Z' | '_' | '0'..'9')*;

// alias id to state_var and packet_field
state_var : ID;
packet_field : ID;

// list of state_var
state_var_with_comma : ',' state_var;
state_vars : state_var
           | state_var state_var_with_comma+;

// list of packet_field
packet_field_with_comma : ',' packet_field;
packet_fields : packet_field
              | packet_field packet_field_with_comma+;

// list of guarded_update
guarded_update_with_comma : ',' guarded_update;
guarded_updates : guarded_update
                | guarded_update guarded_update_with_comma+;

guarded_update : guard ':' update;
guard  : 'rel_op' '(' expr ',' expr ')';
update : state_var '=' expr;
expr   : state_var
       | packet_field
       | expr op=('+'|'-'|'*'|'/') expr
       | '(' expr ')'
       | 'Mux3' '(' expr ',' expr ',' expr ')'
       | 'Mux2' '(' expr ',' expr ')'
       | 'Opt' '(' expr ')'
       | 'Constant';

instruction: state_vars packet_fields guarded_updates;
