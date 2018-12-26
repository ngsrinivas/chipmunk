
#include <iostream>
#include <fstream>
#include <string>
#include <map>
#include <vector>
#include <algorithm>

//if c is an alphabet return 1 else return 0
int start_val(char c){
    if ((c-'a'>=0 && c-'a'<=25) || (c-'A'>=0 && c-'A'<=25))
        return 1;
    else
        return 0;
}

//if c is an alphabet or . or _ or [ ] return 1 else return 0
int var(char c){
    if ((c-'a'>=0 && c-'a'<=25) || (c-'A'>=0 && c-'A'<=25) || (c=='_') || (c == '.')
        || (c=='[') || (c==']') || (c-'0'>=0 && c-'0'<=9))
        return 1;
    else
        return 0;
}

int compare(std::string s1, std::string s2){
    return s1.length() > s2.length();
}

void set_map(std::map<std::string,std::string> &c_to_sk,std::string file_org){
    int count_stateless=0;
    int count_stateful=0;
    
    //location is to store the current position
    std::string::size_type location;
    location = file_org.find('{');
    //curr_str stores the current string
    std::string curr_str;
    curr_str = file_org.substr(location+1,file_org.length()-location-3); //-3 is to remove */
    std::cout<<curr_str.length()<<std::endl;
    int start=0,end=0;
    while (1){
        if (start >= curr_str.length()-1 || end >= curr_str.length()-1)
            break;
        
        while ((!start_val(curr_str[start]) && start<=curr_str.length()-1))
            start++;
        end = start+1;
        while (var(curr_str[end]) && end<=curr_str.length()-1)
            end++;
        
        if (start >= curr_str.length()-1 || end >= curr_str.length()-1)
            break;
        
        //fill the map
        std::string s=curr_str.substr(start,end-start);
        
        //ignore that the variable is if
        if (s[0] == 'i' && s[1] == 'f'){
            start = end+1;
            continue;
        }else if (s.find("else")==0){
            start = end+1;
            continue;
        }
        
        std::map<std::string,std::string>::iterator it;
        it = c_to_sk.find(s);
        if (it == c_to_sk.end()){
            std::string name;
            //stateless
            if (s.find('.')!=std::string::npos && s.find('[')==std::string::npos){
                name = "state_and_packet.pkt_" + std::to_string(count_stateless);
                count_stateless++;
            }
            else{
                name = "state_and_packet.state_" + std::to_string(count_stateful);
                count_stateful++;
            }
            c_to_sk[s] = name;
        }
        start = end+1;
    }
    
}
void replace (std::map<std::string,std::string> c_to_sk,std::string &new_program,std::vector<std::string> key_value){
    
    for(int i=0;i!=key_value.size();i++){
        //var avoid replace p.dstport with p.dst
        while(new_program.find(key_value[i])!=std::string::npos){
            new_program.replace(new_program.find(key_value[i]),key_value[i].length(),c_to_sk[key_value[i]]);
        }
    }
}

void print_usage() {
    std::cerr << "Usage: <source_file> <input_file>" << std::endl;
}

int main(int argc, const char * argv[]) {
    
    if (argc > 2) {
        print_usage();
        return EXIT_FAILURE;
    }
    
    // Get cmdline args
    std::string filename = argv[1];
    std::ifstream inFile(filename.c_str());
    
    std::string str_temp; // store a whole line as a string
    int flag = 0; // whether void has appeared or not
    std::string target_str = "func"; //find the void function
    std::string file_org = "/*";  //original code
    //establish a map
    std::map<std::string,std::string> c_to_sk;
    
    while(getline(inFile,str_temp)){
        //step1: delete the // and /*
        std::size_t found = str_temp.find("//");
        if (found!=std::string::npos){
            if (found == 0)
                continue;
            str_temp = str_temp.substr(0,found);
        }
        found = str_temp.find("/*");
        if (found!=std::string::npos){
            if (found == 0)
                continue;
            str_temp = str_temp.substr(0,found);
        }
        //catch the constant
        if (str_temp.find("define")!=std::string::npos){
            std::vector<std::string> temp;
            int start=str_temp.length()-1,end=str_temp.length()-1;
        //    std::cout<<str_temp[end-1]<<std::endl; //length-1 is the last character
            while (str_temp[end]==' '){
                end--;
            }
            start=end-1;
            while (1){
                if (temp.size()==2)
                    break;
 
                while (str_temp[start]!=' '){
                    start--;
                }
                temp.push_back(str_temp.substr(start+1,end-start));
                if (str_temp[start] == ' ')
                    start--;
                end=start;
            }
            c_to_sk[temp[temp.size()-1]]=temp[temp.size()-2];
            continue;
        }

        if (!flag){
            std::size_t found = str_temp.find(target_str);
            if (found!=std::string::npos){
                flag = 1;
                file_org += str_temp;
                file_org += "\n";
            }
        }else{
            std::size_t found = str_temp.find("//");
            if (found!=std::string::npos){
                if (found == 0)
                    continue;
                file_org += str_temp.substr(0,found);
            }else{
                file_org += str_temp;
            }
            file_org += "\n";
        }
    }
    file_org += "*/";

    //deal with file_org and first copy it into a string new_program
    std::string new_program = file_org;
    set_map(c_to_sk,new_program);
    
    //get all the key value of the map
    std::vector<std::string> key_value;
    
    for(std::map<std::string,std::string>::const_iterator it = c_to_sk.begin();
        it != c_to_sk.end(); ++it){
        key_value.push_back(it->first);
    }
    //sort the key value by their length
    sort(key_value.begin(),key_value.end(),compare);
    
    //replace the parts in new_program
    replace(c_to_sk,new_program,key_value);
    
    std::string::size_type location;
    location = new_program.find('{');
    new_program = new_program.substr(location, new_program.length()-location-4);
    new_program = "|StateAndPacket| program (|StateAndPacket| state_and_packet)" + new_program;
    new_program += " return state_and_packet;\n";
    new_program +='}';
    
    std::ofstream outfile;
    outfile.open("result.sk");
 
    for(std::map<std::string,std::string>::const_iterator it = c_to_sk.begin();
    it != c_to_sk.end(); ++it){
        if (it->second[0]-'0'>=0 && it->second[0]-'0'<=9)
            outfile << "// " <<it->first << "=" << it->second << "\n";
    }
 
    outfile << std::endl;
    for(std::map<std::string,std::string>::const_iterator it = c_to_sk.begin();
    it != c_to_sk.end(); ++it){
        if (it->second.find("state_and_packet.pkt_")!=std::string::npos)
            outfile << "// " <<it->first << "=" << it->second << "\n";
    }
    
    outfile << std::endl;
    for(std::map<std::string,std::string>::const_iterator it = c_to_sk.begin();
    it != c_to_sk.end(); ++it){
        if (it->second.find("state_and_packet.state_")!=std::string::npos)
            outfile << "// " <<it->first << "=" << it->second << "\n";
    }
    outfile << std::endl;
    outfile << file_org << std::endl;
    outfile << std::endl;
    outfile << new_program << std::endl;
    outfile.close();
    
    return 0;
    }
