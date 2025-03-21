import unittest
from codehem.core.manipulator.factory import get_code_manipulator

class TestTypeScriptDecoratorEdgeCases(unittest.TestCase):
    
    def setUp(self):
        self.manipulator = get_code_manipulator('typescript')
    
    def test_class_decorators(self):
        original_code = '''
@Component({
  selector: 'app-user',
  template: '<div>User Component</div>'
})
class UserComponent {
  constructor() {}
}
'''
        
        new_class = '''
@Component({
  selector: 'app-user',
  template: '<div>{{ user?.name || "Unknown User" }}</div>',
  styleUrls: ['./user.component.css']
})
class UserComponent implements OnInit {
  @Input() user: User;
  
  constructor(private userService: UserService) {}
  
  ngOnInit() {
    if (!this.user) {
      this.userService.getDefaultUser()
        .subscribe(user => this.user = user);
    }
  }
}
'''
        
        modified_code = self.manipulator.replace_class(original_code, 'UserComponent', new_class)
        
        # Verify decorators are preserved
        self.assertIn('@Component({', modified_code)
        self.assertIn("  selector: 'app-user',", modified_code)
        self.assertIn("  template: '<div>{{ user?.name || \"Unknown User\" }}</div>',", modified_code)
        self.assertIn("  styleUrls: ['./user.component.css']", modified_code)
        self.assertIn('})', modified_code)
        self.assertIn('class UserComponent implements OnInit {', modified_code)
        self.assertIn('  @Input() user: User;', modified_code)
    
    def test_property_decorators(self):
        original_code = '''
class FormComponent {
  @Input() data: any;
}
'''
        
        new_class = '''
class FormComponent {
  @Input() data: any;
  
  @Input() 
  @Required
  formId: string;
  
  @Output() 
  submitted = new EventEmitter<any>();
  
  @ViewChild('form')
  formElement: ElementRef;
}
'''
        
        modified_code = self.manipulator.replace_class(original_code, 'FormComponent', new_class)
        
        # Verify property decorators
        self.assertIn('class FormComponent {', modified_code)
        self.assertIn('  @Input() data: any;', modified_code)
        self.assertIn('  @Input()', modified_code)
        self.assertIn('  @Required', modified_code)
        self.assertIn('  formId: string;', modified_code)
        self.assertIn('  @Output()', modified_code)
        self.assertIn('  submitted = new EventEmitter<any>();', modified_code)
        self.assertIn('  @ViewChild(\'form\')', modified_code)
        self.assertIn('  formElement: ElementRef;', modified_code)
    
    def test_method_decorators(self):
        original_code = '''
class ApiController {
  @Get('/users')
  findAllUsers() {
    return [];
  }
}
'''
        
        new_method = '''
@Get('/users')
@UseGuards(AuthGuard)
@ApiOperation({ summary: 'Get all users' })
findAllUsers(
  @Query('page') page: number = 1,
  @Query('limit') limit: number = 10
) {
  return this.userService.findAll({
    page,
    limit,
    relations: ['profile', 'roles']
  });
}
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'ApiController', 'findAllUsers', new_method)
        
        # Verify method decorators
        self.assertIn('  @Get(\'/users\')', modified_code)
        self.assertIn('  @UseGuards(AuthGuard)', modified_code)
        self.assertIn('  @ApiOperation({ summary: \'Get all users\' })', modified_code)
        self.assertIn('  findAllUsers(', modified_code)
        self.assertIn('    @Query(\'page\') page: number = 1,', modified_code)
        self.assertIn('    @Query(\'limit\') limit: number = 10', modified_code)
        self.assertIn('  ) {', modified_code)
    
    def test_parameter_decorators(self):
        original_code = '''
class UserController {
  constructor(private userService: UserService) {}
  
  @Post()
  createUser(@Body() userData: CreateUserDto) {
    return this.userService.create(userData);
  }
}
'''
        
        new_method = '''
@Post()
@UsePipes(new ValidationPipe())
createUser(
  @Body() userData: CreateUserDto,
  @Headers('authorization') token: string,
  @Req() request: Request,
  @CurrentUser() currentUser: User
) {
  this.logger.log(`User creation attempt by ${currentUser.username}`);
  
  if (!this.authService.hasPermission(currentUser, 'create:users')) {
    throw new ForbiddenException('Insufficient permissions');
  }
  
  return this.userService.create(userData, {
    createdBy: currentUser.id,
    ipAddress: request.ip
  });
}
'''
        
        modified_code = self.manipulator.replace_method(original_code, 'UserController', 'createUser', new_method)
        
        # Verify parameter decorators
        self.assertIn('  @Post()', modified_code)
        self.assertIn('  @UsePipes(new ValidationPipe())', modified_code)
        self.assertIn('  createUser(', modified_code)
        self.assertIn('    @Body() userData: CreateUserDto,', modified_code)
        self.assertIn('    @Headers(\'authorization\') token: string,', modified_code)
        self.assertIn('    @Req() request: Request,', modified_code)
        self.assertIn('    @CurrentUser() currentUser: User', modified_code)
        self.assertIn('  ) {', modified_code)
    
    def test_complex_property_decorators(self):
        original_code = '''
class EntityClass {
  @Column()
  name: string;
}
'''
        
        new_class = '''
class EntityClass {
  @PrimaryGeneratedColumn('uuid')
  id: string;
  
  @Column({
    type: 'varchar',
    length: 100,
    unique: true,
    nullable: false
  })
  name: string;
  
  @Column({
    type: 'jsonb',
    default: {}
  })
  @Transform(({ value }) => {
    if (value === null) return {};
    return value;
  })
  metadata: Record<string, any>;
  
  @CreateDateColumn()
  createdAt: Date;
  
  @UpdateDateColumn()
  updatedAt: Date;
}
'''
        
        modified_code = self.manipulator.replace_class(original_code, 'EntityClass', new_class)
        
        # Verify complex property decorators
        self.assertIn('class EntityClass {', modified_code)
        self.assertIn('  @PrimaryGeneratedColumn(\'uuid\')', modified_code)
        self.assertIn('  id: string;', modified_code)
        self.assertIn('  @Column({', modified_code)
        self.assertIn('    type: \'varchar\',', modified_code)
        self.assertIn('    length: 100,', modified_code)
        self.assertIn('    unique: true,', modified_code)
        self.assertIn('    nullable: false', modified_code)
        self.assertIn('  })', modified_code)
        self.assertIn('  @Transform(({ value }) => {', modified_code)
        self.assertIn('    if (value === null) return {};', modified_code)
        self.assertIn('    return value;', modified_code)
        self.assertIn('  })', modified_code)
        self.assertIn('  metadata: Record<string, any>;', modified_code)

if __name__ == '__main__':
    unittest.main()