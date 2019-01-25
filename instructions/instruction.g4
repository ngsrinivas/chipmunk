grammar instruction;

// Hide whitespace, but don't skip it
WS : [ \n\t\r]+ -> channel(HIDDEN);

// Keywords
RELOP : 'rel_op'; // <, >, <=, >=, ==, !=
MUX3  : 'Mux3';   // 3-to-1 mux
MUX2  : 'Mux2';   // 2-to-1 mux
OPT   : 'Opt';    // Pick either the argument or 0
CONSTANT : 'C()'; // Return a finite constant
TRUE  : 'True';   // Guard corresponding to "always update"

// Identifiers
ID : ('a'..'z' | 'A'..'Z') ('a'..'z' | 'A'..'Z' | '_' | '0'..'9')*;

// alias id to state_var and packet_field
state_var    : ID;
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
guard  : RELOP '(' expr ',' expr ')'
       | TRUE;
update : state_var '=' expr;
expr   : state_var
       | packet_field
       | expr op=('+'|'-'|'*'|'/') expr
       | '(' expr ')'
       | MUX3 '(' expr ',' expr ',' expr ')'
       | MUX2 '(' expr ',' expr ')'
       | OPT '(' expr ')'
       | CONSTANT;

instruction: state_vars packet_fields guarded_updates;
