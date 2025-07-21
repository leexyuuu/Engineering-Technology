<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="160px">
      <el-form-item label="考试名称" prop="name"  style="margin-right:100px;">
        <el-input v-model="form.name"  />
      </el-form-item>
       <el-form-item label="考试须知" prop="instructions">
        <el-input v-model="form.instructions"  
          :autosize="{ minRows: 2, maxRows: 20 }" type="textarea" />
      </el-form-item>
      <el-form-item label="考试开始时间" prop="start_time">
        <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择日期时间" />
      </el-form-item>
       <el-form-item label="考试截止时间" prop="end_time">
        <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择日期时间" />
      </el-form-item>
       <el-form-item label="考试时长（分钟）" prop="duration_minutes">
          <el-input style="width:200px;"   type="number" v-model="form.duration_minutes"  />
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
        description:'',
        instructions:'',
        start_time: '',
        end_time:'',
        duration_minutes:60
      },
      rules: {
        name: [{ required: true, message: '请输入考试名称', trigger: 'blur' }],
        start_time: [{ required: true, message: '请选择考试开始时间', trigger: 'change' }],
        end_time: [{ required: true, message: '请选择考试开始时间', trigger: 'change' }],
        duration_minutes: [{ required: true, message: '请输入考试时长（分钟）', trigger: 'blur' }]
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