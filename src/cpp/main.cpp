#include <iostream>
#include <parser.h>

int main()
{
  OSED::Parser parser("osed.yaml");
  std::cout << parser["osed"] << std::endl;
}
