<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="120px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="密码" prop="password" v-if="!id">
        <el-input v-model="form.password" type="password" />
      </el-form-item>
      <el-form-item label="头像">
        <el-input v-model="form.avatar" placeholder="头像URL" />
      </el-form-item>
      <el-form-item label="性别">
        <el-select v-model="form.gender" placeholder="请选择性别">
          <el-option label="男" value="男" />
          <el-option label="女" value="女" />
        </el-select>
      </el-form-item>
      <el-form-item label="证件号码">
        <el-input v-model="form.id_number" />
      </el-form-item>
      <el-form-item label="准考证号">
        <el-input v-model="form.exam_number" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import { fetchStudent, createStudent, updateStudent } from '@/api/student'
export default {
  data() {
    return {
      form: {
        name: '',
        phone: '',
        password: '',
        avatar: '',
        gender: '',
        id_number: '',
        exam_number: ''
      },
      rules: {
        name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
        phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      },
      id: null
    }
  },
  created() {
    this.id = this.$route.params.id
    if (this.id) {
      fetchStudent(this.id).then(res => {
        const data = res.data || res
        this.form = {
          name: data.name || '',
          phone: data.phone || '',
          password: data.password||'',
          avatar: data.avatar || '',
          gender: data.gender || '',
          id_number: data.id_number || '',
          exam_number: data.exam_number || ''
        }
      })
    }
  },
  methods: {
    onSubmit() {
      this.$refs.form.validate(valid => {
        if (!valid) return
        const submitData = { ...this.form }
        if (this.id && !submitData.password) {
          //delete submitData.password
        }
        const action = this.id ? updateStudent(this.id, submitData) : createStudent(submitData)
     
        action.then(response => {
              this.$message.success('保存成功')
              this.$router.push({ path: '/student/studentlist' })
            }).catch(err => {
        
              console.log(err)
       
            })
      })
    }
  }
}
</script> 