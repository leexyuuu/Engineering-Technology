<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="100px">
      <el-form-item label="考试名称" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="考试时间" prop="date">
        <el-date-picker v-model="form.date" type="datetime" placeholder="选择日期时间" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import { fetchExam, createExam, updateExam } from '@/api/exam'
export default {
  data() {
    return {
      form: {
        name: '',
        date: ''
      },
      rules: {
        name: [{ required: true, message: '请输入考试名称', trigger: 'blur' }],
        date: [{ required: true, message: '请选择考试时间', trigger: 'change' }]
      },
      id: null
    }
  },
  created() {
    this.id = this.$route.params.id
    if (this.id) {
      fetchExam(this.id).then(res => {
        this.form = res.data || res
      })
    }
  },
  methods: {
    onSubmit() {
      this.$refs.form.validate(valid => {
        if (!valid) return
        const action = this.id ? updateExam(this.id, this.form) : createExam(this.form)
        action.then(() => {
          this.$message.success('保存成功')
          this.$router.push({ path: '/exam/examlist' })
        })
      })
    }
  }
}
</script> 